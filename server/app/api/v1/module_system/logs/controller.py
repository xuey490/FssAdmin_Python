"""日志路由 /api/core/logs/*。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.module_system.logs.service import LogService
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission

LogsRouter = APIRouter(tags=["系统日志"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


def _parse_ids(request: Request, body: dict) -> list[int]:
    raw = body.get("ids")
    if raw is None:
        raw = request.query_params.get("ids")
    if raw is None:
        raw = body.get("id")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [int(x) for x in raw.split(",") if x.strip()]
    if isinstance(raw, list):
        return [int(x) for x in raw]
    return [int(raw)]


@LogsRouter.get("/core/logs/getLoginLogPageList")
async def login_log_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:logs:login"]))):
    return _ok(await LogService(auth).login_page(dict(request.query_params)))


@LogsRouter.delete("/core/logs/deleteLoginLog")
async def login_log_delete(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:logs:deleteLogin"]))):
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    ids = _parse_ids(request, body)
    if not ids:
        return ErrorResponse(msg="请选择要删除的记录", code=1)
    count = await LogService(auth).delete_login(ids)
    return _ok({"count": count, "deleted": count}, "删除成功")


@LogsRouter.get("/core/logs/getOperLogPageList")
async def oper_log_list(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:logs:Oper"]))):
    return _ok(await LogService(auth).oper_page(dict(request.query_params)))


@LogsRouter.delete("/core/logs/deleteOperLog")
async def oper_log_delete(request: Request, auth: AuthSchema = Depends(AuthPermission(permissions=["core:logs:deleteOper"]))):
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    ids = _parse_ids(request, body)
    if not ids:
        return ErrorResponse(msg="请选择要删除的记录", code=1)
    count = await LogService(auth).delete_oper(ids)
    return _ok({"count": count, "deleted": count}, "删除成功")
