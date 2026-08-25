from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")

# ── 日志注入 ──
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(cid: str) -> Token:
    return _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


def reset_correlation_id(token: Token) -> None:
    _correlation_id.reset(token)


# ── 租户 / 用户上下文（对齐 phpserver TenantContext）──
current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
_ignore_tenant_depth: ContextVar[int] = ContextVar("ignore_tenant_depth", default=0)
_ignore_soft_delete_depth: ContextVar[int] = ContextVar("ignore_soft_delete_depth", default=0)


def set_current_tenant(tenant_id: int | None) -> None:
    current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> int | None:
    return current_tenant_id.get()


def clear_current_tenant() -> None:
    current_tenant_id.set(None)


def set_current_user(user_id: int | None) -> None:
    current_user_id.set(user_id)


def get_current_user_id() -> int | None:
    return current_user_id.get()


def clear_current_user() -> None:
    current_user_id.set(None)


def clear_request_audit_context() -> None:
    """请求结束时清理租户/用户上下文。"""
    clear_current_tenant()
    clear_current_user()


def should_apply_tenant() -> bool:
    """对齐 PHP TenantContext::shouldApplyTenant：未 ignore 且租户 ID 有效。"""
    if _ignore_tenant_depth.get() > 0:
        return False
    tid = get_current_tenant_id()
    return tid is not None and int(tid) > 0


def should_apply_soft_delete() -> bool:
    return _ignore_soft_delete_depth.get() <= 0


@contextmanager
def with_ignore_tenant() -> Iterator[None]:
    """临时忽略租户隔离（对齐 PHP TenantContext::withIgnore）。"""
    token = _ignore_tenant_depth.set(_ignore_tenant_depth.get() + 1)
    try:
        yield
    finally:
        _ignore_tenant_depth.reset(token)


@contextmanager
def with_ignore_soft_delete() -> Iterator[None]:
    """临时忽略软删过滤（含查询与 session.delete→软删转换）。"""
    token = _ignore_soft_delete_depth.set(_ignore_soft_delete_depth.get() + 1)
    try:
        yield
    finally:
        _ignore_soft_delete_depth.reset(token)


def run_ignore_tenant(fn: Callable[[], T]) -> T:
    with with_ignore_tenant():
        return fn()


def run_ignore_soft_delete(fn: Callable[[], T]) -> T:
    with with_ignore_soft_delete():
        return fn()


# ── request.state.ctx ──

@dataclass
class RequestContext:
    jwt_payload: Any = None
    jwt_user_info: dict[str, Any] | None = None
    session_id: str | None = None
    user_id: int | None = None
    user_username: str | None = None
    session_info: dict[str, Any] | None = None
    login_location: str | None = None
