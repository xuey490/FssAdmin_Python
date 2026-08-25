from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.post.service import PostService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

PostRouter = APIRouter(route_class=OperationLogRoute, prefix="/post", tags=["岗位管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@PostRouter.get("/list")
async def post_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    return _ok(await PostService(auth).get_list(dict(request.query_params)))


@PostRouter.get("/detail/{id}")
async def detail(id: int, auth: AuthSchema = Depends(get_current_user)):
    data = await PostService(auth).get_detail(id)
    return _ok(data) if data else ErrorResponse(msg="岗位不存在", code=404)


@PostRouter.post("/create")
async def create(request: Request, auth: AuthSchema = Depends(AuthPermission())):
    try:
        return _ok(await PostService(auth).create(await _body(request), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@PostRouter.put("/update/{id}")
async def update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    try:
        await PostService(auth).update(id, await _body(request), auth.user.id)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@PostRouter.delete("/delete/{id}")
async def delete(id: int, auth: AuthSchema = Depends(AuthPermission())):
    await PostService(auth).delete(id)
    return _ok({})


@PostRouter.put("/status/{id}")
async def status(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission())):
    body = await _body(request)
    # 前端可能传 status 或 enabled
    val = body.get("status", body.get("enabled", 1))
    await PostService(auth).update_status(id, int(val))
    return _ok({})


@PostRouter.get("/enabled")
async def enabled(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await PostService(auth).get_all_enabled())


@PostRouter.get("/access-post")
async def access_post(auth: AuthSchema = Depends(get_current_user)):
    """用户编辑弹窗岗位下拉（对齐 phpserver post.accessPost）。"""
    return _ok(await PostService(auth).get_access_post())
