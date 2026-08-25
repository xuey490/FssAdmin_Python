"""邮件日志 /api/core/email/*。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.email_log.service import EmailLogService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission

EmailLogRouter = APIRouter(tags=["邮件日志"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


@EmailLogRouter.get("/core/email/index")
async def email_index(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:email:index"]))):
    return _ok(await EmailLogService(auth).get_list(dict(request.query_params)))


@EmailLogRouter.delete("/core/email/destroy")
async def email_destroy(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:email:destroy"]))):
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    raw = body.get("ids") or request.query_params.get("ids") or body.get("id")
    ids: list[int] = []
    if isinstance(raw, str):
        ids = [int(x) for x in raw.split(",") if x.strip()]
    elif isinstance(raw, list):
        ids = [int(x) for x in raw]
    elif raw is not None:
        ids = [int(raw)]
    if not ids:
        return ErrorResponse(msg="请选择要删除的记录", code=1)
    count = await EmailLogService(auth).destroy(ids)
    return _ok({"count": count}, "删除成功")
