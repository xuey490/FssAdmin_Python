from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.user.service import UserService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

UserRouter = APIRouter(route_class=OperationLogRoute, prefix="/user", tags=["用户管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


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
async def user_create(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:save"]))):
    try:
        return _ok(await UserService(auth).create(await _body(request), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/update/{id}", summary="更新用户")
async def user_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:update"]))):
    try:
        return _ok(await UserService(auth).update(id, await _body(request), auth.user.id))
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
async def user_status(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:status"]))):
    body = await _body(request)
    await UserService(auth).update_status(id, int(body.get("status", 1)))
    return _ok({})


@UserRouter.put("/reset-password/{id}")
async def reset_password(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:resetPassword"]))):
    body = await _body(request)
    try:
        await UserService(auth).reset_password(id, body.get("password") or "123456")
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/change-password/{id}")
async def change_password(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:changePassword"]))):
    try:
        await UserService(auth).change_password(id, await _body(request))
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@UserRouter.put("/clear-cache/{id}")
async def clear_cache(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:clearCache"]))):
    await UserService(auth).clear_cache(id)
    return _ok({})


@UserRouter.put("/set-home-page/{id}")
async def set_home_page(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:home"]))):
    body = await _body(request)
    await UserService(auth).set_home_page(id, body.get("dashboard") or "work")
    return _ok({})


@UserRouter.get("/menus/{id}")
async def get_user_menus(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:read"]))):
    return _ok(await UserService(auth).get_menus(id))


@UserRouter.put("/menus/{id}")
async def save_user_menus(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:user:update"]))):
    body = await _body(request)
    await UserService(auth).save_menus(id, body.get("menu_ids") or [], auth.user.id)
    return _ok({})
