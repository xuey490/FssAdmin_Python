from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.dept.service import DeptService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

DeptRouter = APIRouter(route_class=OperationLogRoute, prefix="/dept", tags=["部门管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@DeptRouter.get("/list")
async def dept_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await DeptService(auth).get_list(dict(request.query_params)))


@DeptRouter.get("/tree")
async def dept_tree(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await DeptService(auth).get_tree())


@DeptRouter.get("/all-enabled")
async def all_enabled(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await DeptService(auth).get_all_enabled())


@DeptRouter.get("/access-dept")
async def access_dept(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await DeptService(auth).get_access_dept())


@DeptRouter.get("/detail/{id}")
async def detail(id: int, auth: AuthSchema = Depends(get_current_user)):
    data = await DeptService(auth).get_detail(id)
    return _ok(data) if data else ErrorResponse(msg="部门不存在", code=404)


@DeptRouter.post("/create")
async def create(request: Request, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await DeptService(auth).create(await _body(request), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DeptRouter.put("/update/{id}")
async def update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await DeptService(auth).update(id, await _body(request), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DeptRouter.delete("/delete/{id}")
async def delete(id: int, auth: AuthSchema = Depends(AuthPermission())):
    await DeptService(auth).delete(id)
    return _ok({})


@DeptRouter.put("/status/{id}")
async def status(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    body = await _body(request)
    await DeptService(auth).update_status(id, int(body.get("status", 1)))
    return _ok({})


@DeptRouter.get("/children/{id}")
async def children(id: int, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await DeptService(auth).get_children_ids(id))
