"""附件管理 /api/system/attachment*。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.v1.module_system.attachment.service import AttachmentCategoryService, AttachmentService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

AttachmentRouter = APIRouter(route_class=OperationLogRoute, prefix="/attachment", tags=["附件管理"])
AttachmentCategoryRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/attachment-category", tags=["附件分类"]
)


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


@AttachmentRouter.get("/list")
async def attachment_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:index"]))):
    return _ok(await AttachmentService(auth).get_list(dict(request.query_params)))


@AttachmentRouter.get("/detail/{id}")
async def attachment_detail(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:index"]))):
    data = await AttachmentService(auth).get_detail(id)
    if not data:
        return ErrorResponse(msg="附件不存在", code=404)
    return _ok(data)


@AttachmentRouter.post("/upload")
async def attachment_upload(
    request: Request,
    file: UploadFile | None = File(None),
    category_id: int = Form(1),
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"])),
):
    try:
        # 勿用 request.base_url：含 root_path=/api，会拼出 /api/uploads 导致预览 404
        return _ok(await AttachmentService(auth).upload(file, category_id=category_id), "上传成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@AttachmentRouter.put("/update/{id}")
async def attachment_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    body = await _body(request)
    try:
        await AttachmentService(auth).update_name(id, str(body.get("origin_name") or ""))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@AttachmentRouter.delete("/delete/{id}")
async def attachment_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    await AttachmentService(auth).delete(id)
    return _ok([], "删除成功")


@AttachmentRouter.delete("/batchDelete")
async def attachment_batch_delete(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    body = await _body(request)
    ids = body.get("ids") or []
    if isinstance(ids, str):
        ids = [int(x) for x in ids.split(",") if x.strip()]
    elif isinstance(ids, int):
        ids = [ids]
    count = await AttachmentService(auth).batch_delete([int(x) for x in ids])
    return _ok({"count": count}, "删除成功")


@AttachmentRouter.put("/move")
async def attachment_move(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    body = await _body(request)
    ids = body.get("ids") or []
    if isinstance(ids, str):
        ids = [int(x) for x in ids.split(",") if x.strip()]
    category_id = int(body.get("category_id") or 0)
    count = await AttachmentService(auth).move([int(x) for x in ids], category_id)
    return _ok({"count": count}, "移动成功")


@AttachmentRouter.get("/download/{id}")
async def attachment_download(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:index"]))):
    svc = AttachmentService(auth)
    data = await svc.get_detail(id)
    if not data:
        return ErrorResponse(msg="附件不存在", code=404)
    path = svc.resolve_path(str(data.get("storage_path") or ""))
    if not path.is_file():
        return ErrorResponse(msg="文件不存在或已被删除", code=1)
    return FileResponse(path=path, filename=data.get("origin_name") or "download", media_type="application/octet-stream")


@AttachmentRouter.get("/stats")
async def attachment_stats(auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:index"]))):
    return _ok(await AttachmentService(auth).stats())


@AttachmentCategoryRouter.get("/list")
async def category_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:index"]))):
    return _ok(await AttachmentCategoryService(auth).get_list(dict(request.query_params)))


@AttachmentCategoryRouter.get("/detail/{id}")
async def category_detail(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:index"]))):
    data = await AttachmentCategoryService(auth).get_detail(id)
    if not data:
        return ErrorResponse(msg="分类不存在", code=404)
    return _ok(data)


@AttachmentCategoryRouter.post("/create")
async def category_create(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    try:
        return _ok(await AttachmentCategoryService(auth).create(await _body(request)), "创建成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@AttachmentCategoryRouter.put("/update/{id}")
async def category_update(id: int, request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    try:
        await AttachmentCategoryService(auth).update(id, await _body(request))
        return _ok([], "更新成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@AttachmentCategoryRouter.delete("/delete/{id}")
async def category_delete(id: int, auth: AuthSchema = Depends(AuthPermission(permissions=["core:attachment:edit"]))):
    await AttachmentCategoryService(auth).delete(id)
    return _ok([], "删除成功")
