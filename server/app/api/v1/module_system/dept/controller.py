from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.dept.schema import DeptCreateSchema, DeptUpdateSchema
from app.api.v1.module_system.dept.service import DeptService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, StatusSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

DeptRouter = APIRouter(route_class=OperationLogRoute, prefix="/dept", tags=["部门管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


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
async def create(data: DeptCreateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await DeptService(auth).create(data.model_dump(exclude_none=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DeptRouter.put("/update/{id}")
async def update(id: int, data: DeptUpdateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await DeptService(auth).update(id, data.model_dump(exclude_unset=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@DeptRouter.delete("/delete/{id}")
async def delete(id: int, auth: AuthSchema = Depends(AuthPermission())):
    await DeptService(auth).delete(id)
    return _ok({})


@DeptRouter.put("/status/{id}")
async def status(id: int, data: StatusSchema, auth: AuthSchema = Depends(AuthPermission())):
    await DeptService(auth).update_status(id, data.status)
    return _ok({})


@DeptRouter.get("/children/{id}")
async def children(id: int, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await DeptService(auth).get_children_ids(id))
