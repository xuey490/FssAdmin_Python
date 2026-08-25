"""数据字典 /api/system/dict/*。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.dict.service import DictService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

DictRouter = APIRouter(route_class=OperationLogRoute, prefix="/dict", tags=["数据字典"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@DictRouter.get("/type/list")
async def type_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:index"]))):
    return _ok(await DictService(auth).type_list(dict(request.query_params)))


@DictRouter.get("/type/detail/{id}")
async def type_detail(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:index"]))):
    data = await DictService(auth).type_detail(id)
    if not data:
        return ErrorResponse(msg="字典类型不存在", code=404)
    return _ok(data)


@DictRouter.post("/type/create")
async def type_create(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    try:
        return _ok(await DictService(auth).type_create(await _body(request)), "创建成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DictRouter.put("/type/update/{id}")
async def type_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    try:
        await DictService(auth).type_update(id, await _body(request))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DictRouter.delete("/type/delete/{id}")
async def type_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    await DictService(auth).type_delete(id)
    return _ok([], "删除成功")


@DictRouter.put("/type/status/{id}")
async def type_status(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    body = await _body(request)
    await DictService(auth).type_status(id, int(body.get("status", 1)))
    return _ok([])


@DictRouter.get("/data/list")
async def data_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:index"]))):
    return _ok(await DictService(auth).data_list(dict(request.query_params)))


@DictRouter.get("/data/code/{dictCode}")
async def data_by_code(dictCode: str, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:index"]))):
    return _ok(await DictService(auth).data_by_code(dictCode))


@DictRouter.get("/data/detail/{id}")
async def data_detail(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:index"]))):
    data = await DictService(auth).data_detail(id)
    if not data:
        return ErrorResponse(msg="字典数据不存在", code=404)
    return _ok(data)


@DictRouter.post("/data/create")
async def data_create(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    try:
        return _ok(await DictService(auth).data_create(await _body(request)), "创建成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DictRouter.put("/data/update/{id}")
async def data_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    try:
        await DictService(auth).data_update(id, await _body(request))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DictRouter.delete("/data/delete/{id}")
async def data_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    await DictService(auth).data_delete(id)
    return _ok([], "删除成功")


@DictRouter.delete("/data/batchDelete")
async def data_batch_delete(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    body = await _body(request)
    ids = body.get("ids") or []
    if isinstance(ids, str):
        ids = [int(x) for x in ids.split(",") if x.strip()]
    count = await DictService(auth).data_batch_delete([int(x) for x in ids])
    return _ok({"count": count}, "删除成功")


@DictRouter.put("/data/status/{id}")
async def data_status(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:dict:edit"]))):
    body = await _body(request)
    await DictService(auth).data_status(id, int(body.get("status", 1)))
    return _ok([])
