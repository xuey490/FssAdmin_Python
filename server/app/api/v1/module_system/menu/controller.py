from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.menu.schema import MenuCreateSchema, MenuUpdateSchema
from app.api.v1.module_system.menu.service import MenuService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, StatusSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

MenuRouter = APIRouter(route_class=OperationLogRoute, prefix="/menu", tags=["菜单管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


@MenuRouter.get("/list")
async def menu_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_list(dict(request.query_params)))


@MenuRouter.get("/tree")
async def menu_tree(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_tree())


@MenuRouter.get("/user-tree")
async def user_tree(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_user_menu_tree())


@MenuRouter.get("/user-permissions")
async def user_permissions(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_user_permissions())


@MenuRouter.get("/permission-tree")
async def permission_tree(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_permission_tree())


@MenuRouter.get("/access-menu")
async def access_menu(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_access_menu())


@MenuRouter.get("/assignable-tree")
async def assignable_tree(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await MenuService(auth).get_assignable_tree())


@MenuRouter.get("/detail/{id}")
async def detail(id: int, auth: AuthSchema = Depends(get_current_user)):
    data = await MenuService(auth).get_detail(id)
    return _ok(data) if data else ErrorResponse(msg="菜单不存在", code=404)


@MenuRouter.post("/create")
async def create(data: MenuCreateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await MenuService(auth).create(data.model_dump(exclude_none=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@MenuRouter.put("/update/{id}")
async def update(id: int, data: MenuUpdateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        data_out = await MenuService(auth).update(id, data.model_dump(exclude_unset=True), auth.user.id)
        return _ok(data_out) if data_out else ErrorResponse(msg="菜单不存在", code=404)
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@MenuRouter.delete("/delete/{id}")
async def delete(id: int, auth: AuthSchema = Depends(AuthPermission())):
    await MenuService(auth).delete(id)
    return _ok({})


@MenuRouter.put("/status/{id}")
async def status(id: int, data: StatusSchema, auth: AuthSchema = Depends(AuthPermission())):
    await MenuService(auth).update_status(id, data.status)
    return _ok({})
