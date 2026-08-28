from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.tenant.schema import (
    TenantCreateSchema,
    TenantDefaultSchema,
    TenantFlagSchema,
    TenantUpdateSchema,
    TenantUsersSchema,
)
from app.api.v1.module_system.tenant.service import TenantService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, StatusSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

TenantRouter = APIRouter(route_class=OperationLogRoute, prefix="/tenant", tags=["租户管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


@TenantRouter.get("/list")
async def tenant_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await TenantService(auth).get_list(dict(request.query_params)))


@TenantRouter.get("/detail/{id}")
async def detail(id: int, auth: AuthSchema = Depends(get_current_user)):
    data = await TenantService(auth).get_detail(id)
    return _ok(data) if data else ErrorResponse(msg="租户不存在", code=404)


@TenantRouter.post("/create")
async def create(data: TenantCreateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await TenantService(auth).create(data.model_dump(exclude_none=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@TenantRouter.put("/update/{id}")
async def update(id: int, data: TenantUpdateSchema, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await TenantService(auth).update(id, data.model_dump(exclude_unset=True), auth.user.id))
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
async def status(id: int, data: StatusSchema, auth: AuthSchema = Depends(AuthPermission())):
    await TenantService(auth).update_status(id, data.status)
    return _ok({})


@TenantRouter.get("/users/{tenantId}")
async def users(tenantId: int, request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await TenantService(auth).get_tenant_users(tenantId, dict(request.query_params)))


@TenantRouter.get("/available-users/{tenantId}")
async def available_users(tenantId: int, request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await TenantService(auth).get_available_users(tenantId, dict(request.query_params)))


@TenantRouter.post("/add-users/{tenantId}")
async def add_users(tenantId: int, data: TenantUsersSchema, auth: AuthSchema = Depends(AuthPermission())):
    n = await TenantService(auth).add_users(tenantId, data.user_ids, auth.user.id)
    return _ok({"added": n})


@TenantRouter.delete("/remove-user/{tenantId}/{userId}")
async def remove_user(tenantId: int, userId: int, auth: AuthSchema = Depends(AuthPermission())):
    await TenantService(auth).remove_user(tenantId, userId)
    return _ok({})


@TenantRouter.put("/set-admin/{tenantId}/{userId}")
async def set_admin(tenantId: int, userId: int, data: TenantFlagSchema, auth: AuthSchema = Depends(AuthPermission())):
    await TenantService(auth).set_admin(tenantId, userId, data.is_super)
    return _ok({})


@TenantRouter.put("/set-default/{tenantId}/{userId}")
async def set_default(tenantId: int, userId: int, data: TenantDefaultSchema, auth: AuthSchema = Depends(AuthPermission())):
    await TenantService(auth).set_default(tenantId, userId, data.is_default)
    return _ok({})
