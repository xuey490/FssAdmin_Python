"""在线用户路由 — 对齐 web: GET /api/monitor/online/list 、 DELETE /api/monitor/online/:token。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, redis_getter
from app.core.router_class import OperationLogRoute

from .schema import OnlineQueryParam
from .service import OnlineService

OnlineRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/monitor/online",
    tags=["系统监控", "在线用户"],
)


@OnlineRouter.get(
    "/list",
    summary="在线用户列表",
    response_model=ResponseSchema[dict],
)
async def online_list(
    request: Request,
    redis: Annotated[Redis, Depends(redis_getter)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    search: Annotated[OnlineQueryParam, Depends()],
    auth: AuthSchema = Depends(AuthPermission(permissions=["monitor:online:list"])),
) -> JSONResponse:
    _ = auth
    if not search.user_name:
        search.user_name = (
            request.query_params.get("userName") or request.query_params.get("username") or ""
        ).strip()
    if not search.ipaddr:
        search.ipaddr = (request.query_params.get("ipaddr") or "").strip()
    data = await OnlineService.get_online_list(redis=redis, search=search, db=db)
    return SuccessResponse(data=data, msg="获取成功")


@OnlineRouter.delete(
    "/{token}",
    summary="强制下线",
    response_model=ResponseSchema[None],
)
async def online_force_logout(
    token: str,
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: AuthSchema = Depends(AuthPermission(permissions=["monitor:online:forceLogout"])),
) -> JSONResponse:
    _ = auth
    await OnlineService.delete_online(redis=redis, session_id=token)
    return SuccessResponse(msg="强退成功")
