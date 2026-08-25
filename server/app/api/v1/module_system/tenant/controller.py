from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.tenant.service import TenantService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

TenantRouter = APIRouter(route_class=OperationLogRoute, prefix="/tenant", tags=["租户管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@TenantRouter.get("/list")
async def tenant_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await TenantService(auth).get_list(dict(request.query_params)))


@TenantRouter.get("/detail/{id}")
async def detail(id: int, auth: AuthSchema = Depends(get_current_user)):
    data = await TenantService(auth).get_detail(id)
    return _ok(data) if data else ErrorResponse(msg="租户不存在", code=404)


@TenantRouter.post("/create")
async def create(request: Request, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await TenantService(auth).create(await _body(request), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@TenantRouter.put("/update/{id}")
async def update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await TenantService(auth).update(id, await _body(request), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@TenantRouter.delete("/delete/{id}")
async def delete(id: int, auth: AuthSchema = Depends(AuthPermission())):
    try:
        await TenantService(auth).delete(id)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@TenantRouter.put("/status/{id}")
async def status(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    body = await _body(request)
    await TenantService(auth).update_status(id, int(body.get("status", 1)))
    return _ok({})


@TenantRouter.get("/users/{tenantId}")
async def users(tenantId: int, request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await TenantService(auth).get_tenant_users(tenantId, dict(request.query_params)))


@TenantRouter.get("/available-users/{tenantId}")
async def available_users(tenantId: int, request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await TenantService(auth).get_available_users(tenantId, dict(request.query_params)))


@TenantRouter.post("/add-users/{tenantId}")
async def add_users(tenantId: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    body = await _body(request)
    n = await TenantService(auth).add_users(tenantId, body.get("user_ids") or [], auth.user.id)
    return _ok({"added": n})


@TenantRouter.delete("/remove-user/{tenantId}/{userId}")
async def remove_user(tenantId: int, userId: int, auth: AuthSchema = Depends(AuthPermission())):
    await TenantService(auth).remove_user(tenantId, userId)
    return _ok({})


@TenantRouter.put("/set-admin/{tenantId}/{userId}")
async def set_admin(tenantId: int, userId: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    body = await _body(request)
    await TenantService(auth).set_admin(tenantId, userId, int(body.get("is_super", 0)))
    return _ok({})


@TenantRouter.put("/set-default/{tenantId}/{userId}")
async def set_default(tenantId: int, userId: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    body = await _body(request)
    await TenantService(auth).set_default(tenantId, userId, int(body.get("is_default", 0)))
    return _ok({})
