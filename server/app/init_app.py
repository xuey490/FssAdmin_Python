from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter, WebSocketRateLimiter

from app.core import cache_util

from .config.setting import settings
from .core.exceptions import handle_exception
from .core.http_limit import http_limit_callback, ws_limit_callback
from .core.logger import logger
from .utils.common_util import import_modules_async
from .utils.console import console_end, console_start


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    try:
        await import_modules_async(modules=settings.EVENT_LIST, desc="全局事件", app=app, status=True)
        from app.core.timezone import tz_name

        logger.info("时区 {}", tz_name())
        logger.info("✅ 全局事件模块加载完成")
        # ponytail: 旧 plugin/platform 调度器有循环依赖，本阶段跳过
        try:
            await cache_util.init(redis=app.state.redis)
            logger.info("✅ fastapi-admin-cache 初始化完成")
        except Exception as e:
            logger.warning("⏭️ cache 初始化跳过: {}", e)
        limiter_ready = False
        if settings.DEMO_ENABLE:
            logger.warning("演示模式已开启：禁止 POST/PUT/PATCH/DELETE（登录/刷新/登出除外）")
        if settings.RATE_LIMIT_ENABLED:
            redis = getattr(app.state, "redis", None)
            if redis is None:
                logger.warning("⏭️ RATE_LIMIT_ENABLED 但 Redis 不可用，跳过限流初始化")
            else:
                from .core.http_limit import ip_identifier

                await FastAPILimiter.init(
                    redis=redis,
                    prefix=settings.REQUEST_LIMITER_REDIS_PREFIX,
                    identifier=ip_identifier,
                    http_callback=http_limit_callback,
                    ws_callback=ws_limit_callback,
                )
                limiter_ready = True
                logger.info(
                    "✅ 请求限流器初始化完成 ({}次/{}秒)",
                    settings.RATE_LIMIT_TIMES,
                    settings.RATE_LIMIT_SECONDS,
                )
        else:
            logger.info("⏭️ 请求限流已关闭 (RATE_LIMIT_ENABLED=false)")

        scheduler_ready = False
        if settings.SCHEDULER_ENABLE:
            try:
                from app.core.ap_scheduler import SchedulerUtil

                await SchedulerUtil.init_scheduler(redis=getattr(app.state, "redis", None))
                scheduler_ready = True
                logger.info("✅ APScheduler 初始化完成")
            except Exception as e:
                logger.warning("⏭️ 调度器初始化失败: {}", e)
        else:
            logger.info("⏭️ 调度器已关闭 (SCHEDULER_ENABLE=false)")

        # 视频下载/元数据队列：确保表存在 + 启动工人 + 崩溃恢复
        try:
            from app.api.v1.module_platform.video.downloader import DownloadQueue
            from app.api.v1.module_platform.video.meta_queue import MetaFetchQueue
            from app.api.v1.module_platform.video.model import VideoDownloadModel, VideoModel
            from app.core.database import async_engine

            async with async_engine.begin() as conn:
                await conn.run_sync(VideoModel.__table__.create, checkfirst=True)
                await conn.run_sync(VideoDownloadModel.__table__.create, checkfirst=True)
            MetaFetchQueue.instance().start()
            DownloadQueue.instance().start()
            logger.info(
                "✅ 视频队列已启动 (meta_recover_on_start={}, ytdlp_subprocess={})",
                settings.VIDEO_META_RECOVER_ON_START,
                settings.VIDEO_YTDLP_SUBPROCESS,
            )
        except Exception as e:
            logger.warning("⏭️ 视频队列启动失败: {}", e)

        try:
            console_start(
                host=settings.SERVER_HOST,
                port=settings.SERVER_PORT,
                reload=settings.ENVIRONMENT,
                database_ready=True,
                redis_ready=True,
                scheduler_ready=scheduler_ready,
                limiter_ready=limiter_ready,
            )
        except Exception as e:
            logger.warning("console_start skipped: {}", e)
    except Exception as e:
        logger.error("app init failed: {}", e)
        raise SystemExit(1)

    yield

    try:
        try:
            from app.api.v1.module_platform.video.downloader import DownloadQueue
            from app.api.v1.module_platform.video.meta_queue import MetaFetchQueue

            MetaFetchQueue.instance().stop()
            DownloadQueue.instance().stop(reason="服务关闭")
        except Exception as e:
            logger.warning("video queues stop skipped: {}", e)
        if settings.SCHEDULER_ENABLE:
            try:
                from app.core.ap_scheduler import SchedulerUtil

                await SchedulerUtil.shutdown(wait=False)
            except Exception as e:
                logger.warning("scheduler shutdown skipped: {}", e)
        try:
            await cache_util.clear()
        except Exception:
            pass
        if settings.RATE_LIMIT_ENABLED and FastAPILimiter.redis is not None:
            await FastAPILimiter.close()
        await import_modules_async(modules=settings.EVENT_LIST, desc="全局事件", app=app, status=False)
        from app.core.database import async_engine

        await async_engine.dispose()
        console_end()
    except Exception as e:
        logger.error("❌ 应用关闭过程中发生错误: {}", e)
        raise SystemExit(1)


def register_middlewares(app: FastAPI) -> None:
    from .utils.common_util import import_module

    for middleware in settings.MIDDLEWARE_LIST[::-1]:
        if not middleware:
            continue
        middleware = import_module(middleware, desc="中间件")
        app.add_middleware(middleware)


def register_exceptions(app: FastAPI) -> None:
    handle_exception(app)


def register_routers(app: FastAPI) -> None:
    from app.api.v1.module_common import common_router
    from app.api.v1.module_monitor import CoreServerRouter, DatabaseRouter, monitor_router
    from app.api.v1.module_system import CoreRouter, system_router

    # 全局限流：单 IP 每分钟最多 RATE_LIMIT_TIMES；关闭时不挂依赖
    rate_deps = (
        [Depends(RateLimiter(times=settings.RATE_LIMIT_TIMES, seconds=settings.RATE_LIMIT_SECONDS))]
        if settings.RATE_LIMIT_ENABLED
        else []
    )
    app.include_router(common_router, dependencies=rate_deps)
    app.include_router(CoreRouter, dependencies=rate_deps)
    app.include_router(CoreServerRouter, dependencies=rate_deps)
    app.include_router(DatabaseRouter, dependencies=rate_deps)
    app.include_router(monitor_router, dependencies=rate_deps)
    app.include_router(system_router, dependencies=rate_deps)

    # ponytail: 整包 platform_router 目前被 email.UserMixin 等阻塞；视频模块单独挂载
    from fastapi import APIRouter

    from app.api.v1.module_platform.article.controller import ArticleRouter
    from app.api.v1.module_platform.video.controller import VideoRouter

    platform_video = APIRouter(prefix="/platform")
    platform_video.include_router(VideoRouter)
    app.include_router(platform_video, dependencies=rate_deps)
    # Vue 调 /api/article/*，不套 /platform
    app.include_router(ArticleRouter, dependencies=rate_deps)

    # 动态插件 discover 停用；仅显式挂载 cronjob
    from app.plugin.module_task.cronjob.job.controller import JobRouter
    from app.plugin.module_task.cronjob.node.controller import NodeRouter

    task_router = APIRouter(prefix="/task")
    task_router.include_router(NodeRouter)
    task_router.include_router(JobRouter)
    app.include_router(task_router, dependencies=rate_deps)


def register_files(app: FastAPI) -> None:
    # ponytail: root_path=/api 时 StaticFiles Mount 会把 /static/x 错解析成 static/static/x → 404；
    # 与 /uploads 一样用显式 FileResponse，兼容直链 /static 与 /uploads
    from pathlib import Path

    from fastapi.responses import FileResponse
    from starlette.responses import Response

    from app.config.path_conf import BASE_DIR

    def _safe_file(root: Path, file_path: str) -> Path | None:
        target = (root / file_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return None
        return target if target.is_file() else None

    if settings.STATIC_ENABLE:
        static_root = Path(settings.STATIC_ROOT).resolve()
        static_root.mkdir(parents=True, exist_ok=True)
        static_url = settings.STATIC_URL.rstrip("/") or "/static"

        @app.get(f"{static_url}/{{file_path:path}}", include_in_schema=False)
        async def serve_static(file_path: str) -> Response:
            target = _safe_file(static_root, file_path)
            if target is None:
                return Response(status_code=404)
            return FileResponse(target)

    upload_root = (BASE_DIR / "uploads").resolve()
    upload_root.mkdir(parents=True, exist_ok=True)

    @app.get("/uploads/{file_path:path}", include_in_schema=False)
    async def serve_upload(file_path: str) -> Response:
        target = _safe_file(upload_root, file_path)
        if target is None:
            return Response(status_code=404)
        return FileResponse(target)


def reset_api_docs(app: FastAPI) -> None:
    swagger_ui_redirect_url = str(app.swagger_ui_oauth2_redirect_url)

    @app.get(settings.DOCS_URL, include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=swagger_ui_redirect_url,
            swagger_js_url=settings.SWAGGER_JS_URL,
            swagger_css_url=settings.SWAGGER_CSS_URL,
            swagger_favicon_url=settings.FAVICON_URL,
        )

    @app.get(swagger_ui_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()

    @app.get(settings.REDOC_URL, include_in_schema=False)
    async def redoc_html() -> HTMLResponse:
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url=settings.REDOC_JS_URL,
            redoc_favicon_url=settings.FAVICON_URL,
        )
