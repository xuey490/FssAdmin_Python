import time
import uuid
from types import MappingProxyType

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.common.response import ErrorResponse
from app.config.setting import get_settings
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.operation_log import should_record_oper_log, write_operation_log
from app.core.request_context import (
    clear_request_audit_context,
    reset_correlation_id,
    set_correlation_id,
    set_current_tenant,
)
from app.core.token_manager import build_token_manager
from app.utils.ip_local_util import get_client_ip


def _strip_bearer(authorization: str) -> str | None:
    v = authorization.strip()
    if v[:7].lower() == "bearer ":
        v = v[7:].strip()
    elif v[:6].lower() == "bearer":
        v = v[6:].strip()
    else:
        return None
    return v or None


_DEFAULT_CONFIG: MappingProxyType = MappingProxyType({
    "demo_enable": False,
    "ip_white_list": (),
    "ip_black_list": (),
    "white_api_list_path": (),
})

# 演示模式仍需登录；这些 POST 不改业务数据
_DEMO_AUTH_ALLOW = (
    "/core/login",
    "/core/logout",
    "/core/refresh",
    "/auth/login",
    "/auth/logout",
    "/auth/refresh",
)


def demo_write_allowed(method: str, path: str, *, enabled: bool) -> bool:
    """演示模式只允许读，以及登录/刷新/登出。"""
    if not enabled:
        return True
    if method.upper() in ("GET", "HEAD", "OPTIONS"):
        return True
    if path.startswith("/api/"):
        path = path[4:]
    return any(path == allow or path.startswith(allow + "/") for allow in _DEMO_AUTH_ALLOW)


class CustomCORSMiddleware(CORSMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        cfg = get_settings()
        super().__init__(
            app,
            allow_origins=cfg.ALLOWED_ORIGINS,
            allow_methods=cfg.ALLOW_METHODS,
            allow_headers=cfg.ALLOW_HEADERS,
            allow_credentials=cfg.ALLOW_CREDENTIALS,
            expose_headers=cfg.CORS_EXPOSE_HEADERS,
            max_age=cfg.CORS_MAX_AGE,
        )


class RequestLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        client_ip = get_client_ip(request)
        logger.info("请求: {} {} | client={}", request.method, request.url.path, client_ip or "unknown")
        try:
            if not demo_write_allowed(
                request.method,
                str(request.url.path),
                enabled=get_settings().DEMO_ENABLE,
            ):
                logger.warning("演示模式拦截: {} {}", request.method, request.url.path)
                return ErrorResponse(msg="演示环境，禁止修改数据", code=403)
            response = await call_next(request)
            process_time = round(time.time() - start_time, 5)
            response.headers["X-Process-Time"] = str(process_time)
            logger.info("响应: {} | {:.1f}ms", response.status_code, process_time * 1000)
            return response
        except CustomException as e:
            logger.exception(f"中间件异常: {e!s}")
            return ErrorResponse(msg="系统异常，请联系管理员", data=str(e))


class CustomGZipMiddleware(GZipMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app, minimum_size=get_settings().GZIP_MIN_SIZE, compresslevel=get_settings().GZIP_COMPRESS_LEVEL)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        self._header = "X-Correlation-ID"
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(self._header) or str(uuid.uuid4())
        token = set_correlation_id(cid)
        try:
            response = await call_next(request)
            response.headers[self._header] = cid
            return response
        finally:
            reset_correlation_id(token)


_TENANT_WHITELIST_PREFIXES = (
    "/docs", "/redoc", "/openapi.json", "/metrics", "/static/",
    "/core/login", "/core/captcha", "/core/refresh", "/core/tenants-by-username",
    "/core/config/", "/common/health", "/health",
)


def _tenant_is_whitelisted(path: str) -> bool:
    # web 双 /api 经代理后可能仍带 /api 前缀
    if path.startswith("/api/"):
        path = path[4:]
    for prefix in _TENANT_WHITELIST_PREFIXES:
        if path == prefix or path.startswith(prefix):
            return True
    return False


async def _extract_tenant_from_token(request: Request) -> int | None:
    """对齐 phpserver TenantMiddleware：JWT 优先，Header 仅作无 JWT 时的兜底。"""
    if hasattr(request.state, "tenant_id_resolved"):
        return getattr(request.state, "tenant_id", None)

    request.state.tenant_id_resolved = True
    request.state.tenant_id = None

    # 1) Token claims（切换租户后新 token 为准；勿被前端残留的 X-Tenant-Id 覆盖）
    token = _strip_bearer(request.headers.get("Authorization", ""))
    if token:
        try:
            redis = getattr(request.app.state, "redis", None)
            payload = await build_token_manager(redis).parse_token(token)
            tid = int(getattr(payload, "tenant_id", 0) or 0) if payload else 0
            if tid > 0:
                request.state.tenant_id = tid
                return request.state.tenant_id
        except Exception:
            pass

    # 2) Header 兜底（调试 / 无 JWT claims 场景）
    header_tid = request.headers.get("X-Tenant-Id") or request.headers.get("X-Tenant-ID")
    if header_tid and str(header_tid).isdigit() and int(header_tid) > 0:
        request.state.tenant_id = int(header_tid)
        return request.state.tenant_id

    return request.state.tenant_id


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        try:
            if not _tenant_is_whitelisted(request.url.path):
                try:
                    set_current_tenant(await _extract_tenant_from_token(request))
                except Exception:
                    logger.exception("租户中间件异常: path={}", request.url.path)
            return await call_next(request)
        finally:
            clear_request_audit_context()


class OperationLogMiddleware(BaseHTTPMiddleware):
    """全局写操作日志，对齐 phpserver OperationLogMiddleware。

    对非白名单 POST/PUT/PATCH/DELETE：先缓存 body（供下游与落库），再执行业务，最后异步写库。
    multipart 不读整包，只记占位，避免大文件进内存。
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method.upper()
        path = str(request.url.path)
        if not should_record_oper_log(method, path):
            return await call_next(request)

        started = time.perf_counter()
        body_text = ""
        content_type = (request.headers.get("content-type") or "").lower()
        try:
            if "multipart/form-data" in content_type:
                body_text = '{"_multipart":true}'
            else:
                # 必须在 call_next 前读一次，BaseHTTPMiddleware 才会把 body 缓存给下游
                raw = await request.body()
                if raw:
                    body_text = raw.decode("utf-8", errors="ignore")[:2000]
        except Exception:
            body_text = ""

        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        try:
            await write_operation_log(request, body_text=body_text, duration_ms=duration_ms)
        except Exception as e:
            logger.warning("operation log middleware skipped: {}", e)
        return response
