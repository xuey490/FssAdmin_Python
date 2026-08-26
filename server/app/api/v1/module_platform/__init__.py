"""platform 包 — 延迟组装路由，避免 import service 时拉起全部 controller。"""

from fastapi import APIRouter

__all__ = ["platform_router"]


def __getattr__(name: str):
    if name != "platform_router":
        raise AttributeError(name)

    from app.api.v1.module_platform.plugin.controller import PluginRouter
    from app.api.v1.module_platform.video.controller import VideoRouter

    router = APIRouter(prefix="/platform")
    router.include_router(PluginRouter)
    router.include_router(VideoRouter)
    return router
