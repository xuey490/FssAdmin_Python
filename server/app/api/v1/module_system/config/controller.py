"""系统设置路由 /api/core/config*（对齐 web + phpserver）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.config.service import ConfigService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

ConfigRouter = APIRouter(route_class=OperationLogRoute, tags=["系统设置"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _parse_ids(body: dict, query: dict | None = None) -> list[int]:
    raw = body.get("ids")
    if raw is None and query:
        raw = query.get("ids")
    if raw is None:
        raw = body.get("id")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [int(x) for x in raw.split(",") if x.strip()]
    if isinstance(raw, list):
        return [int(x) for x in raw]
    return [int(raw)]


@ConfigRouter.get("/core/configGroup/list")
async def group_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:index"]))):
    return _ok(await ConfigService(auth).group_list(dict(request.query_params)))


@ConfigRouter.post("/core/configGroup/save")
async def group_save(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        return _ok(await ConfigService(auth).group_save(await _body(request)), "保存成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.put("/core/configGroup/update/{id}")
async def group_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        await ConfigService(auth).group_update(id, await _body(request))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.delete("/core/configGroup/delete/{id}")
async def group_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    await ConfigService(auth).group_delete(id)
    return _ok([], "删除成功")


@ConfigRouter.post("/core/configGroup/testEmail")
async def group_test_email(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        data = await ConfigService(auth).test_email(await _body(request))
        return _ok(data, data.get("message") or "邮件发送成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.get("/core/config/public/{key}")
async def public_config(key: str, db: AsyncSession = Depends(db_getter)):
    value = await ConfigService(db=db).get_by_key(key)
    return _ok({"key": key, "value": value})


@ConfigRouter.get("/core/config/list")
async def config_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:index"]))):
    return _ok(await ConfigService(auth).config_list(dict(request.query_params)))


@ConfigRouter.post("/core/config/save")
async def config_save(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        return _ok(await ConfigService(auth).config_save(await _body(request)), "保存成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.put("/core/config/update/{id}")
async def config_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:update"]))):
    try:
        await ConfigService(auth).config_update(id, await _body(request))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.delete("/core/config/delete")
async def config_delete(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    body = await _body(request)
    ids = _parse_ids(body, dict(request.query_params))
    if not ids:
        return ErrorResponse(msg="请选择要删除的记录", code=1)
    count = await ConfigService(auth).config_delete(ids)
    return _ok({"count": count}, "删除成功")


@ConfigRouter.post("/core/config/batchUpdate")
async def config_batch_update(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:update"]))):
    body = await _body(request)
    configs = body.get("config") or body.get("configs") or []
    if not configs:
        return ErrorResponse(msg="配置数据不能为空", code=1)
    try:
        await ConfigService(auth).batch_update(configs)
        return _ok([], "批量更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)
