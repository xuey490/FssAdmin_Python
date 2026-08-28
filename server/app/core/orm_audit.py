"""SQLAlchemy ORM 审计：租户隔离 / 软删 / 时间戳 / 操作人（对齐 phpserver）。

有列才生效；无列跳过。
逃生口：
- with_ignore_tenant() / with_ignore_soft_delete()
- execution_options(skip_tenant=True) / skip_soft_delete=True
硬删：session.execute(delete(...)) 或 with_ignore_soft_delete 下的 session.delete。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, bindparam, event, inspect as sa_inspect
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from app.core.base_model import MappedBase, SaModelMixin, TenantMixin
from app.core.request_context import (
    get_current_tenant_id,
    get_current_user_id,
    should_apply_soft_delete,
    should_apply_tenant,
)
from app.core.timezone import now as beijing_now


def _tenant_bindparam():
    """执行期取值，避免 with_loader_criteria lambda 缓存错租户。"""
    return bindparam(
        "sa_current_tenant_id",
        callable_=lambda: int(get_current_tenant_id() or 0),
        type_=Integer(),
        unique=True,
    )

_column_cache: dict[tuple[type, str], bool] = {}
_registered = False


def has_mapped_column(cls: type, name: str) -> bool:
    """模型是否映射了某列（缓存）。"""
    key = (cls, name)
    if key in _column_cache:
        return _column_cache[key]
    ok = False
    try:
        mapper = sa_inspect(cls)
        ok = name in mapper.columns
    except Exception:
        ok = hasattr(cls, name)
    _column_cache[key] = ok
    return ok


def clear_column_cache() -> None:
    _column_cache.clear()


def _instance_has_column(obj: Any, name: str) -> bool:
    try:
        return name in sa_inspect(obj).mapper.columns
    except Exception:
        return hasattr(obj, name)


def _mapped_class_from_dml(stmt: Any) -> type | None:
    desc = getattr(stmt, "entity_description", None)
    if not isinstance(desc, dict):
        return None
    entity = desc.get("entity")
    if entity is None:
        return None
    insp = sa_inspect(entity, raiseerr=False)
    if insp is not None and getattr(insp, "class_", None) is not None:
        return insp.class_
    if isinstance(entity, type):
        return entity
    return None


def _skip_tenant(state: ORMExecuteState) -> bool:
    return bool(state.execution_options.get("skip_tenant")) or not should_apply_tenant()


def _skip_soft_delete(state: ORMExecuteState) -> bool:
    return bool(state.execution_options.get("skip_soft_delete")) or not should_apply_soft_delete()


def _apply_select_filters(state: ORMExecuteState) -> None:
    if state.is_column_load or state.is_relationship_load:
        return

    # 用 mixin 做实体边界，避免 lambda 内调用 Python 函数（SQLAlchemy 禁止）
    if not _skip_soft_delete(state):
        state.statement = state.statement.options(
            with_loader_criteria(
                SaModelMixin,
                lambda cls: cls.delete_time.is_(None),
                include_aliases=True,
            )
        )

    if not _skip_tenant(state):
        # 超管也隔离：有租户上下文就过滤（对齐 phpserver LaTenantScope）
        state.statement = state.statement.options(
            with_loader_criteria(
                TenantMixin,
                lambda cls: cls.tenant_id == _tenant_bindparam(),
                include_aliases=True,
            )
        )


def _apply_dml_tenant(state: ORMExecuteState) -> None:
    if _skip_tenant(state):
        return
    cls = _mapped_class_from_dml(state.statement)
    if cls is None or not has_mapped_column(cls, "tenant_id"):
        return
    tid = int(get_current_tenant_id() or 0)
    if tid <= 0:
        return
    state.statement = state.statement.where(cls.tenant_id == tid)


def _on_do_orm_execute(state: ORMExecuteState) -> None:
    if state.is_select:
        _apply_select_filters(state)
    elif state.is_update or state.is_delete:
        _apply_dml_tenant(state)


def _is_empty_audit_val(val: Any) -> bool:
    return val is None or val == 0 or val == ""


def _on_before_insert(mapper, connection, target) -> None:  # noqa: ANN001
    now = beijing_now()
    uid = get_current_user_id()

    if has_mapped_column(type(target), "tenant_id") and should_apply_tenant():
        tid = get_current_tenant_id()
        if tid is not None and int(tid) > 0:
            # 有租户上下文时强制写入当前租户（避免 Mixin default=1 误入）
            target.tenant_id = int(tid)

    if has_mapped_column(type(target), "create_time") and getattr(target, "create_time", None) is None:
        target.create_time = now
    if has_mapped_column(type(target), "update_time") and getattr(target, "update_time", None) is None:
        target.update_time = now

    if uid is not None and int(uid) > 0:
        if has_mapped_column(type(target), "created_by") and _is_empty_audit_val(
            getattr(target, "created_by", None)
        ):
            target.created_by = int(uid)
        if has_mapped_column(type(target), "updated_by") and _is_empty_audit_val(
            getattr(target, "updated_by", None)
        ):
            target.updated_by = int(uid)


def _on_before_update(mapper, connection, target) -> None:  # noqa: ANN001
    now = beijing_now()
    uid = get_current_user_id()
    cls = type(target)

    if has_mapped_column(cls, "update_time"):
        target.update_time = now
    if uid is not None and int(uid) > 0 and has_mapped_column(cls, "updated_by"):
        target.updated_by = int(uid)


def _on_before_flush(session: Session, flush_context, instances) -> None:  # noqa: ANN001, ARG001
    """session.delete → 有 delete_time 则软删（对齐 Eloquent SoftDeletes）。"""
    if not should_apply_soft_delete():
        return
    for obj in list(session.deleted):
        if not _instance_has_column(obj, "delete_time"):
            continue
        if getattr(obj, "delete_time", None) is not None:
            # 已标记软删又被 delete：仍转 UPDATE，避免二次硬删
            pass
        session.deleted.discard(obj)
        obj.delete_time = beijing_now()
        if has_mapped_column(type(obj), "update_time"):
            obj.update_time = beijing_now()
        uid = get_current_user_id()
        if uid is not None and int(uid) > 0 and has_mapped_column(type(obj), "updated_by"):
            obj.updated_by = int(uid)


def register_orm_audit() -> None:
    global _registered
    if _registered:
        return
    event.listen(Session, "do_orm_execute", _on_do_orm_execute)
    event.listen(Session, "before_flush", _on_before_flush)
    event.listen(MappedBase, "before_insert", _on_before_insert, propagate=True)
    event.listen(MappedBase, "before_update", _on_before_update, propagate=True)
    _registered = True
