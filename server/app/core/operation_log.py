"""操作日志写入（对齐 phpserver OperationLogMiddleware）。"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.logs.service import LogService
from app.core.database import async_db_session
from app.core.logger import logger
from app.utils.ip_local_util import get_client_ip

# 不记录操作日志的路径前缀（对齐 phpserver OperationLogMiddleware）
# 路径按去 /api 前缀后匹配（代理可能剥掉 /api）
OPER_LOG_WHITELIST = (
    "/core/login",
    "/core/logout",
    "/core/refresh",
    "/core/captcha",
    "/core/tenants-by-username",
    "/system/monitor",
    "/system/redis",
    "/auth/login",
    "/auth/logout",
    "/docs",
    "/redoc",
    "/openapi.json",
)

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_ID_TAIL = re.compile(r"^\d+$")


def is_write_method(method: str) -> bool:
    return method.upper() in _WRITE_METHODS


def normalize_oper_path(path: str) -> str:
    if path.startswith("/api/"):
        return path[4:]
    return path


def is_oper_log_whitelisted(path: str) -> bool:
    path = normalize_oper_path(path)
    for prefix in OPER_LOG_WHITELIST:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return True
    return False


def should_record_oper_log(method: str, path: str) -> bool:
    return is_write_method(method) and not is_oper_log_whitelisted(path)


def service_name_from_path(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return ""
    # /api/system/user/delete/118 -> delete；/api/system/user/create -> create
    if _ID_TAIL.match(parts[-1]) and len(parts) >= 2:
        return parts[-2][:30]
    return parts[-1][:30]


def extract_username(request: Request) -> tuple[str, int | None]:
    # 业务事务回滚后 ORM User 可能已 detach，不能再懒加载属性
    uid = getattr(request.state, "user_id", None)
    auth = getattr(request.state, "auth", None)
    if auth is not None:
        user = getattr(auth, "user", None)
        if user is not None:
            try:
                return str(getattr(user, "username", "") or ""), int(getattr(user, "id", 0) or 0) or None
            except Exception:
                return "", int(uid) if uid else None
        username = getattr(auth, "username", None)
        aid = getattr(auth, "id", None) or getattr(auth, "user_id", None) or uid
        if username:
            return str(username), int(aid) if aid else None
    return "", int(uid) if uid else None


def build_request_data(body_text: str, request: Request) -> str:
    params: dict[str, Any] = {}
    if body_text:
        try:
            decoded = json.loads(body_text)
            if isinstance(decoded, dict):
                params.update(decoded)
            else:
                params["_body"] = decoded
        except Exception:
            params["_raw"] = body_text[:2000]
    # DELETE 常用 query ids=
    for k, v in request.query_params.multi_items():
        if k in params:
            continue
        params[k] = v
    params.pop("password", None)
    params.pop("old_password", None)
    params.pop("new_password", None)
    raw = json.dumps(params, ensure_ascii=False)
    return raw[:2000] if len(raw) > 2000 else raw


async def write_operation_log(
    request: Request,
    *,
    body_text: str = "",
    duration_ms: float = 0,
    db: AsyncSession | None = None,
) -> None:
    username, user_id = extract_username(request)
    path = str(request.url.path)
    payload = build_request_data(body_text, request)

    async def _do(session: AsyncSession) -> None:
        await LogService.write_oper(
            session,
            username=username,
            method=request.method.upper(),
            router=path,
            service_name=service_name_from_path(path),
            ip=get_client_ip(request) or "",
            request_data=payload,
            duration=str(round(duration_ms, 2)),
            created_by=user_id,
        )
        await session.commit()

    try:
        if db is not None:
            await _do(db)
        else:
            async with async_db_session() as session:
                await _do(session)
    except Exception as e:
        logger.warning("operation log write skipped: {}", e)
