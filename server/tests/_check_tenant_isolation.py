"""ponytail: 租户隔离冒烟 — JWT 优先 + ORM 过滤恒带当前租户。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "dev")

from app.core.orm_audit import _tenant_bindparam
from app.core.request_context import (
    clear_request_audit_context,
    get_current_tenant_id,
    set_current_tenant,
    should_apply_tenant,
    with_ignore_tenant,
)


def _check_jwt_before_header_in_source() -> None:
    """中间件 / 依赖里 JWT 解析必须出现在 Header 之前。"""
    root = Path(__file__).resolve().parent / "app" / "core"
    mw = (root / "middlewares.py").read_text(encoding="utf-8")
    dep = (root / "dependencies.py").read_text(encoding="utf-8")
    assert mw.find("parse_token") < mw.find('headers.get("X-Tenant-Id")'), (
        "middleware: token claims must precede Header"
    )
    assert "仅当 JWT 无租户" in dep


def _check_crud_no_super_bypass() -> None:
    src = (Path(__file__).resolve().parent / "app" / "core" / "base_crud.py").read_text(encoding="utf-8")
    assert "not self.auth.user.is_superuser" not in src, "base_crud still bypasses tenant for superuser"
    assert "超管同样隔离" in src or "全站隔离" in src


def _check_context_and_bindparam() -> None:
    clear_request_audit_context()
    assert not should_apply_tenant()
    set_current_tenant(7)
    assert should_apply_tenant() and get_current_tenant_id() == 7
    bp = _tenant_bindparam()
    # BindParameter.callable 在部分 SQLAlchemy 版本是私有实现细节
    fn = getattr(bp, "callable", None)
    assert callable(fn) and fn() == 7
    set_current_tenant(3)
    assert fn() == 3
    with with_ignore_tenant():
        assert not should_apply_tenant()
    assert should_apply_tenant()
    clear_request_audit_context()


def main() -> None:
    _check_jwt_before_header_in_source()
    _check_crud_no_super_bypass()
    _check_context_and_bindparam()
    print("ok: tenant isolation jwt-first + no-super-bypass + bindparam")


if __name__ == "__main__":
    main()
