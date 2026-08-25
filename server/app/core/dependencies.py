from collections.abc import AsyncGenerator, Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import Depends, Request
from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted
from app.api.v1.module_system.user.model import UserModel
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.core.request_context import get_current_tenant_id as _get_ctx_tenant_id
from app.core.request_context import set_current_tenant, set_current_user
from app.core.security import OAuth2Schema
from app.core.token_manager import build_token_manager

F = TypeVar("F", bound=Callable[..., Any])


def require_superadmin(func: F) -> F:
    """实例方法装饰器：要求 auth.user 为超管。"""

    @wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        user = getattr(getattr(self, "auth", None), "user", None)
        if not user or int(getattr(user, "is_super", 0) or 0) != 1:
            raise CustomException(msg="仅超级管理员可操作", code=403, status_code=403)
        return await func(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


async def db_getter() -> AsyncGenerator[AsyncSession, None]:
    async with async_db_session() as session:
        async with session.begin():
            yield session


async def redis_getter(request: Request) -> Redis:
    return request.app.state.redis


async def get_current_tenant_id() -> int | None:
    return _get_ctx_tenant_id()


async def get_current_user(
    request: Request,
    token: str = Depends(OAuth2Schema),
    db: AsyncSession = Depends(db_getter),
) -> AuthSchema:
    if not token:
        raise CustomException(msg="请先登录", code=401, status_code=401)

    redis = getattr(request.app.state, "redis", None)
    claims = await build_token_manager(redis).parse_token(token)
    if claims is None:
        raise CustomException(msg="认证已失效", code=401, status_code=401)

    uid = int(claims.uid or claims.sub or 0)
    if uid <= 0:
        raise CustomException(msg="认证已失效", code=401, status_code=401)

    result = await db.execute(select(UserModel).where(UserModel.id == uid, not_deleted(UserModel)))
    user = result.scalar_one_or_none()
    if not user:
        raise CustomException(msg="用户不存在", code=401, status_code=401)
    if int(user.status or 0) != 1:
        raise CustomException(msg="账号已被禁用", code=403, status_code=403)

    # 对齐 phpserver：JWT.tenant_id 优先；仅当 JWT 无租户时才用 Header
    tenant_id = int(claims.tenant_id or 0)
    if tenant_id <= 0:
        header_tid = request.headers.get("X-Tenant-Id") or request.headers.get("X-Tenant-ID")
        if header_tid and str(header_tid).isdigit() and int(header_tid) > 0:
            tenant_id = int(header_tid)

    set_current_tenant(tenant_id if tenant_id > 0 else None)
    set_current_user(int(user.id))
    auth = AuthSchema(db=db, tenant_id=tenant_id if tenant_id > 0 else None, check_data_scope=False)
    auth.user = user
    request.state.auth = auth
    request.state.user_id = user.id
    request.state.tenant_id = tenant_id
    request.state.access_token = token
    return auth


class AuthPermission:
    """权限校验：超管放行；否则检查 slug 是否在用户权限集合中（懒加载）。"""

    def __init__(self, permissions: list[str] | None = None, check_data_scope: bool = False) -> None:
        self.permissions = permissions or []
        self.check_data_scope = check_data_scope

    async def __call__(self, auth: AuthSchema = Depends(get_current_user)) -> AuthSchema:
        auth.check_data_scope = self.check_data_scope
        if not self.permissions:
            return auth
        user = auth.user
        if user and getattr(user, "is_super", 0):
            return auth
        from app.api.v1.module_system.menu.service import MenuService

        perms = await MenuService(auth).get_user_permissions(user.id)
        if "*" in perms:
            return auth
        for p in self.permissions:
            if p in perms:
                return auth
        raise CustomException(msg="无权限访问", code=403, status_code=403)


# 兼容旧名
async def get_current_user_info(auth: AuthSchema = Depends(get_current_user)) -> AuthSchema:
    return auth
