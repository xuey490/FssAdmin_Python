"""系统设置路由 /api/core/config*（对齐 web + phpserver）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.config.schema import (
    ConfigBatchSchema,
    ConfigGroupSaveSchema,
    ConfigGroupUpdateSchema,
    ConfigSaveSchema,
    ConfigTestEmailSchema,
    ConfigUpdateSchema,
)
from app.api.v1.module_system.config.service import ConfigService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, BatchDelete
from app.core.dependencies import AuthPermission, db_getter
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

ConfigRouter = APIRouter(route_class=OperationLogRoute, tags=["系统设置"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


@ConfigRouter.get("/core/configGroup/list")
async def group_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:index"]))):
    return _ok(await ConfigService(auth).group_list(dict(request.query_params)))


@ConfigRouter.post("/core/configGroup/save")
async def group_save(data: ConfigGroupSaveSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        return _ok(await ConfigService(auth).group_save(data.model_dump(exclude_none=True)), "保存成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.put("/core/configGroup/update/{id}")
async def group_update(id: int, data: ConfigGroupUpdateSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        await ConfigService(auth).group_update(id, data.model_dump(exclude_unset=True))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.delete("/core/configGroup/delete/{id}")
async def group_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    await ConfigService(auth).group_delete(id)
    return _ok([], "删除成功")


@ConfigRouter.post("/core/configGroup/testEmail")
async def group_test_email(data: ConfigTestEmailSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        out = await ConfigService(auth).test_email(data.model_dump())
        return _ok(out, out.get("message") or "邮件发送成功")
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
async def config_save(data: ConfigSaveSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    try:
        return _ok(await ConfigService(auth).config_save(data.model_dump(exclude_none=True)), "保存成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.put("/core/config/update/{id}")
async def config_update(id: int, data: ConfigUpdateSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:update"]))):
    try:
        await ConfigService(auth).config_update(id, data.model_dump(exclude_unset=True))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ConfigRouter.delete("/core/config/delete")
async def config_delete(data: BatchDelete, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:edit"]))):
    count = await ConfigService(auth).config_delete(data.ids)
    return _ok({"count": count}, "删除成功")


@ConfigRouter.post("/core/config/batchUpdate")
async def config_batch_update(data: ConfigBatchSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:config:update"]))):
    if not data.config:
        return ErrorResponse(msg="配置数据不能为空", code=1)
    try:
        await ConfigService(auth).batch_update([item.model_dump() for item in data.config])
        return _ok([], "批量更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)
