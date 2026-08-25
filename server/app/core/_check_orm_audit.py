"""ponytail: ORM 审计自检 — 列探测 + ignore 开关。运行: python -m app.core._check_orm_audit"""

from __future__ import annotations

from app.core.orm_audit import clear_column_cache, has_mapped_column
from app.core.request_context import (
    clear_request_audit_context,
    get_current_tenant_id,
    set_current_tenant,
    set_current_user,
    should_apply_soft_delete,
    should_apply_tenant,
    with_ignore_soft_delete,
    with_ignore_tenant,
)


def _check_ignore_switches() -> None:
    clear_request_audit_context()
    assert not should_apply_tenant(), "no tenant → should not apply"
    assert should_apply_soft_delete(), "soft-delete on by default"

    set_current_tenant(1)
    assert should_apply_tenant()
    with with_ignore_tenant():
        assert not should_apply_tenant()
        with with_ignore_tenant():
            assert not should_apply_tenant()
        assert not should_apply_tenant()
    assert should_apply_tenant()

    with with_ignore_soft_delete():
        assert not should_apply_soft_delete()
    assert should_apply_soft_delete()

    set_current_tenant(0)
    assert not should_apply_tenant(), "tenant_id=0 → skip"
    clear_request_audit_context()


def _check_column_detect() -> None:
    clear_column_cache()
    # 延迟导入避免无 DB 时牵出引擎；模型元数据即可
    from app.api.v1.module_system.dept.model import DeptModel
    from app.api.v1.module_system.menu.model import MenuModel
    from app.api.v1.module_system.user.model import UserDeptModel, UserModel

    assert has_mapped_column(DeptModel, "tenant_id")
    assert has_mapped_column(DeptModel, "delete_time")
    assert has_mapped_column(DeptModel, "created_by")
    assert has_mapped_column(DeptModel, "create_time")

    assert not has_mapped_column(MenuModel, "tenant_id"), "menu is global"
    assert has_mapped_column(MenuModel, "delete_time")
    assert has_mapped_column(MenuModel, "created_by")

    assert not has_mapped_column(UserModel, "tenant_id"), "user is global"
    assert has_mapped_column(UserModel, "delete_time")

    assert has_mapped_column(UserDeptModel, "tenant_id")
    assert not has_mapped_column(UserDeptModel, "delete_time"), "user_dept hard-delete table"
    assert issubclass(UserDeptModel, __import__("app.core.base_model", fromlist=["TenantMixin"]).TenantMixin)
    assert has_mapped_column(UserDeptModel, "create_time")


def main() -> None:
    _check_ignore_switches()
    _check_column_detect()
    set_current_user(9)
    set_current_tenant(2)
    assert get_current_tenant_id() == 2
    clear_request_audit_context()
    assert get_current_tenant_id() is None
    print("ok: orm_audit context + column detect")


if __name__ == "__main__":
    main()
