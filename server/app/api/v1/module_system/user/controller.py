from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.user.schema import (
    DashboardSchema,
    ResetPasswordSchema,
    UserChangePasswordSchema,
    UserCreateSchema,
    UserMenusSchema,
    UserUpdateSchema,
)
from app.api.v1.module_system.user.service import UserService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, StatusSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

UserRouter = APIRouter(route_class=OperationLogRoute, prefix="/user", tags=["用户管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


@UserRouter.get("/list", summary="用户列表")
async def user_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:index"]))):
    return _ok(await UserService(auth).get_list(dict(request.query_params)))


@UserRouter.get("/detail/{id}", summary="用户详情")
async def user_detail(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:read"]))):
    data = await UserService(auth).get_detail(id)
    if not data:
        return ErrorResponse(msg="用户不存在", code=404)
    return _ok(data)


@UserRouter.post("/create", summary="创建用户")
async def user_create(data: UserCreateSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:save"]))):
    try:
        return _ok(await UserService(auth).create(data.model_dump(exclude_none=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/update/{id}", summary="更新用户")
async def user_update(id: int, data: UserUpdateSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:update"]))):
    try:
        return _ok(await UserService(auth).update(id, data.model_dump(exclude_unset=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.delete("/delete/{id}", summary="删除用户")
async def user_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:delete"]))):
    try:
        await UserService(auth).delete(id)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/status/{id}", summary="更新状态")
async def user_status(id: int, data: StatusSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:status"]))):
    await UserService(auth).update_status(id, data.status)
    return _ok({})


@UserRouter.put("/reset-password/{id}")
async def reset_password(id: int, data: ResetPasswordSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:resetPassword"]))):
    try:
        await UserService(auth).reset_password(id, data.password)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/change-password/{id}")
async def change_password(id: int, data: UserChangePasswordSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:changePassword"]))):
    try:
        await UserService(auth).change_password(id, {"password": data.new_password})
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/clear-cache/{id}")
async def clear_cache(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:clearCache"]))):
    await UserService(auth).clear_cache(id)
    return _ok({})


@UserRouter.put("/set-home-page/{id}")
async def set_home_page(id: int, data: DashboardSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:home"]))):
    await UserService(auth).set_home_page(id, data.dashboard)
    return _ok({})


@UserRouter.get("/menus/{id}")
async def get_user_menus(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:read"]))):
    return _ok(await UserService(auth).get_menus(id))


@UserRouter.put("/menus/{id}")
async def save_user_menus(id: int, data: UserMenusSchema, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:update"]))):
    await UserService(auth).save_menus(id, data.menu_ids, auth.user.id)
    return _ok({})
