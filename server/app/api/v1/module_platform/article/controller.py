from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_platform.article.schema import ArticleCreateSchema, ArticleUpdateSchema
from app.api.v1.module_platform.article.service import ArticleService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, BatchDelete, StatusSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

ArticleRouter = APIRouter(route_class=OperationLogRoute, prefix="/article", tags=["文章管理"])


def _ok(data: Any = None) -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {})


@ArticleRouter.get("/list", summary="文章列表")
async def article_list(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["module_platform:article:index", "article:index"])),
):
    return _ok(await ArticleService(auth).get_list(dict(request.query_params)))


@ArticleRouter.get("/detail/{id}", summary="文章详情")
async def article_detail(
    id: int,
    auth: AuthSchema = Depends(AuthPermission(permissions=["module_platform:article:index", "article:index"])),
):
    data = await ArticleService(auth).get_detail(id)
    if not data:
        return ErrorResponse(msg="文章不存在", code=404)
    return _ok(data)


@ArticleRouter.post("/create", summary="创建文章")
async def article_create(
    data: ArticleCreateSchema,
    auth: AuthSchema = Depends(AuthPermission(permissions=["module_platform:article:create", "article:create"])),
):
    try:
        return _ok(await ArticleService(auth).create(data.model_dump(exclude_none=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ArticleRouter.put("/update/{id}", summary="更新文章")
async def article_update(
    id: int,
    data: ArticleUpdateSchema,
    auth: AuthSchema = Depends(AuthPermission(permissions=["module_platform:article:update", "article:update"])),
):
    try:
        return _ok(await ArticleService(auth).update(id, data.model_dump(exclude_unset=True), auth.user.id))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ArticleRouter.delete("/delete", summary="删除文章")
async def article_delete(
    data: BatchDelete,
    auth: AuthSchema = Depends(AuthPermission(permissions=["module_platform:article:delete", "article:delete"])),
):
    try:
        await ArticleService(auth).delete(data.ids)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@ArticleRouter.put("/status/{id}", summary="更新状态")
async def article_status(
    id: int,
    data: StatusSchema,
    auth: AuthSchema = Depends(AuthPermission(permissions=["module_platform:article:update", "article:update"])),
):
    try:
        await ArticleService(auth).update_status(id, data.status)
        return _ok({})
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)
