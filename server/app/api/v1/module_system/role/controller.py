from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.role.schema import RoleCreateSchema, RoleMenusSchema, RoleUpdateSchema
from app.api.v1.module_system.role.service import RoleService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, StatusSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

RoleRouter = APIRouter(route_class=OperationLogRoute, prefix="/role", tags=["角色管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


@RoleRouter.get("/list")
async def role_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await RoleService(auth).get_list(dict(request.query_params)))


@RoleRouter.get("/all")
async def role_all(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await RoleService(auth).get_all())


@RoleRouter.get("/tree")
async def role_tree(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await RoleService(auth).get_tree())


@RoleRouter.get("/access-role")
async def access_role(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await RoleService(auth).get_access_role())


@RoleRouter.get("/detail/{id}")
async def detail(id: int, auth: AuthSchema = Depends(get_current_user)):
    data = await RoleService(auth).get_detail(id)
    return _ok(data) if data else ErrorResponse(msg="角色不存在", code=404)


@RoleRouter.post("/create")
async def create(data: RoleCreateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await RoleService(auth).create(data.model_dump(exclude_none=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@RoleRouter.put("/update/{id}")
async def update(id: int, data: RoleUpdateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await RoleService(auth).update(id, data.model_dump(exclude_unset=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@RoleRouter.delete("/delete/{id}")
async def delete(id: int, auth: AuthSchema = Depends(AuthPermission())):
    try:
        await RoleService(auth).delete(id)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@RoleRouter.put("/status/{id}")
async def status(id: int, data: StatusSchema, auth: AuthSchema = Depends(AuthPermission())):
    await RoleService(auth).update_status(id, data.status)
    return _ok({})


@RoleRouter.put("/assign-menus/{id}")
async def assign_menus(id: int, data: RoleMenusSchema, auth: AuthSchema = Depends(AuthPermission())):
    await RoleService(auth).assign_menus(id, data.menu_ids, auth.user.id)
    return _ok({})


@RoleRouter.put("/menu-permission/{id}")
async def menu_permission(id: int, data: RoleMenusSchema, auth: AuthSchema = Depends(AuthPermission())):
    return await assign_menus(id, data, auth)


@RoleRouter.get("/menu-by-role/{id}")
async def menu_by_role(id: int, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await RoleService(auth).menu_by_role(id))
