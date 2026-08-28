"""多租户数据权限（对齐 PHP DataScopeTrait：强制租户 + 6 档 data_scope）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.api.v1.module_system.common import not_deleted
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.role.model import RoleDeptModel, RoleModel
from app.api.v1.module_system.user.model import UserDeptModel, UserRoleModel
from app.core.base_schema import AuthSchema

DATA_SCOPE_ALL = 1
DATA_SCOPE_DEPT = 2
DATA_SCOPE_DEPT_AND_CHILD = 3
DATA_SCOPE_SELF = 4
DATA_SCOPE_DEPT_AND_SELF = 5
DATA_SCOPE_CUSTOM = 6


@dataclass(frozen=True)
class ScopeDecision:
    deny_all: bool = False
    tenant_id: int | None = None
    skip_business: bool = False
    dept_ids: tuple[int, ...] | None = None
    created_by: int | None = None
    or_created_by: bool = False


def resolve_scope_decision(
    *,
    user_id: int | None,
    tenant_id: int | None,
    is_super: bool,
    role_ids: list[int],
    data_scope: int,
    dept_id: int,
    child_dept_ids: list[int],
    custom_dept_ids: list[int],
) -> ScopeDecision:
    """纯函数：把用户上下文收成查询决策（不连库，可单测）。"""
    uid = int(user_id or 0)
    tid = int(tenant_id or 0)
    if uid <= 0 or tid <= 0:
        return ScopeDecision(deny_all=True)

    if is_super or uid == 1 or 1 in role_ids:
        return ScopeDecision(tenant_id=tid, skip_business=True)

    if data_scope == DATA_SCOPE_ALL:
        return ScopeDecision(tenant_id=tid, skip_business=True)

    if data_scope == DATA_SCOPE_DEPT:
        if dept_id > 0:
            return ScopeDecision(tenant_id=tid, dept_ids=(dept_id,))
        return ScopeDecision(tenant_id=tid, created_by=uid)

    if data_scope == DATA_SCOPE_DEPT_AND_CHILD:
        if dept_id > 0:
            ids = tuple(child_dept_ids) if child_dept_ids else (dept_id,)
            return ScopeDecision(tenant_id=tid, dept_ids=ids)
        return ScopeDecision(tenant_id=tid, created_by=uid)

    if data_scope == DATA_SCOPE_SELF:
        return ScopeDecision(tenant_id=tid, created_by=uid)

    if data_scope == DATA_SCOPE_DEPT_AND_SELF:
        if dept_id > 0:
            ids = tuple(child_dept_ids) if child_dept_ids else (dept_id,)
            return ScopeDecision(tenant_id=tid, dept_ids=ids, created_by=uid, or_created_by=True)
        return ScopeDecision(tenant_id=tid, created_by=uid)

    if data_scope == DATA_SCOPE_CUSTOM:
        if custom_dept_ids:
            return ScopeDecision(tenant_id=tid, dept_ids=tuple(custom_dept_ids))
        return ScopeDecision(tenant_id=tid, created_by=uid)

    return ScopeDecision(tenant_id=tid, created_by=uid)


def apply_scope_filters(query: Select, model: type, decision: ScopeDecision) -> Select:
    """把决策落到 SQLAlchemy where。"""
    if decision.deny_all:
        return query.where(false())

    if decision.tenant_id is not None and hasattr(model, "tenant_id"):
        query = query.where(model.tenant_id == decision.tenant_id)

    if decision.skip_business:
        return query

    dept_clause = None
    if decision.dept_ids is not None:
        dept_clause = model.dept_id.in_(list(decision.dept_ids)) if decision.dept_ids else false()

    if decision.or_created_by and dept_clause is not None and decision.created_by is not None:
        return query.where(or_(dept_clause, model.created_by == decision.created_by))
    if decision.created_by is not None:
        return query.where(model.created_by == decision.created_by)
    if dept_clause is not None:
        return query.where(dept_clause)
    return query


async def apply_data_scope(query: Select, model: type, auth: AuthSchema) -> Select:
    decision = await build_scope_decision(auth)
    return apply_scope_filters(query, model, decision)


async def load_user_dept_id(auth: AuthSchema) -> int:
    user = getattr(auth, "user", None)
    user_id = int(getattr(user, "id", 0) or 0) if user else 0
    tenant_id = int(auth.tenant_id or 0)
    if user_id <= 0 or auth.db is None:
        return 0
    return await _load_dept_id(auth.db, user_id, tenant_id)


async def build_scope_decision(auth: AuthSchema) -> ScopeDecision:
    user = getattr(auth, "user", None)
    user_id = int(getattr(user, "id", 0) or 0) if user else 0
    tenant_id = int(auth.tenant_id or 0)
    is_super = bool(user) and int(getattr(user, "is_super", 0) or 0) == 1
    db = auth.db

    if user_id <= 0 or tenant_id <= 0 or db is None:
        return resolve_scope_decision(
            user_id=user_id or None,
            tenant_id=tenant_id or None,
            is_super=is_super,
            role_ids=[],
            data_scope=DATA_SCOPE_SELF,
            dept_id=0,
            child_dept_ids=[],
            custom_dept_ids=[],
        )

    role_ids, data_scope = await _load_roles(db, user_id, tenant_id)
    if is_super or user_id == 1 or 1 in role_ids or data_scope == DATA_SCOPE_ALL:
        return resolve_scope_decision(
            user_id=user_id,
            tenant_id=tenant_id,
            is_super=is_super,
            role_ids=role_ids,
            data_scope=data_scope,
            dept_id=0,
            child_dept_ids=[],
            custom_dept_ids=[],
        )

    dept_id = await _load_dept_id(db, user_id, tenant_id)
    child_dept_ids: list[int] = []
    custom_dept_ids: list[int] = []
    if data_scope in (DATA_SCOPE_DEPT_AND_CHILD, DATA_SCOPE_DEPT_AND_SELF) and dept_id > 0:
        child_dept_ids = await _dept_tree_ids(db, dept_id, tenant_id)
    if data_scope == DATA_SCOPE_CUSTOM and role_ids:
        custom_dept_ids = await _custom_dept_ids(db, role_ids[0])

    return resolve_scope_decision(
        user_id=user_id,
        tenant_id=tenant_id,
        is_super=is_super,
        role_ids=role_ids,
        data_scope=data_scope,
        dept_id=dept_id,
        child_dept_ids=child_dept_ids,
        custom_dept_ids=custom_dept_ids,
    )


async def _load_roles(db: AsyncSession, user_id: int, tenant_id: int) -> tuple[list[int], int]:
    q = select(UserRoleModel.role_id).where(
        UserRoleModel.user_id == user_id, not_deleted(UserRoleModel)
    )
    if tenant_id > 0:
        q = q.where(UserRoleModel.tenant_id == tenant_id)
    role_ids = [int(x) for x in (await db.execute(q)).scalars().all() if x]
    if not role_ids:
        return [], DATA_SCOPE_SELF
    result = await db.execute(select(RoleModel).where(RoleModel.id == role_ids[0], not_deleted(RoleModel)))
    role = result.scalar_one_or_none()
    data_scope = int(getattr(role, "data_scope", DATA_SCOPE_SELF) or DATA_SCOPE_SELF)
    return role_ids, data_scope


async def _load_dept_id(db: AsyncSession, user_id: int, tenant_id: int) -> int:
    q = select(UserDeptModel.dept_id).where(UserDeptModel.user_id == user_id)
    if tenant_id > 0:
        q = q.where(UserDeptModel.tenant_id == tenant_id)
    row = (await db.execute(q.limit(1))).scalar_one_or_none()
    return int(row or 0)


async def _dept_tree_ids(db: AsyncSession, dept_id: int, tenant_id: int) -> list[int]:
    """本部门 + 子部门（对齐 PHP getAllChildIds 含自身）。"""
    q = select(DeptModel).where(not_deleted(DeptModel))
    if tenant_id > 0:
        q = q.where(DeptModel.tenant_id == tenant_id)
    all_depts = list((await db.execute(q)).scalars().all())
    ids: list[int] = [dept_id]

    def walk(pid: int) -> None:
        for d in all_depts:
            if int(d.parent_id or 0) == pid:
                ids.append(d.id)
                walk(d.id)

    walk(dept_id)
    return ids


async def _custom_dept_ids(db: AsyncSession, role_id: int) -> list[int]:
    result = await db.execute(select(RoleDeptModel.dept_id).where(RoleDeptModel.role_id == role_id))
    return [int(x) for x in result.scalars().all() if x]
