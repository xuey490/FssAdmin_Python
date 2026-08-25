"""platform 包 — 延迟组装路由，避免 import service 时拉起全部 controller。"""

from fastapi import APIRouter

__all__ = ["platform_router"]


def __getattr__(name: str):
    if name != "platform_router":
        raise AttributeError(name)

    from app.api.v1.module_platform.email.controller import EmailRouter
    from app.api.v1.module_platform.invoice.controller import PlatformInvoiceRouter, TenantInvoiceRouter
    from app.api.v1.module_platform.menu.controller import MenuRouter
    from app.api.v1.module_platform.order.controller import (
        OrderRouter,
        PaymentRouter,
        RefundRouter,
        TenantOrderRouter,
    )
    from app.api.v1.module_platform.package.controller import PackageRouter
    from app.api.v1.module_platform.plugin.controller import PluginRouter
    from app.api.v1.module_platform.self_service.controller import TenantSelfServiceRouter
    from app.api.v1.module_platform.tenant.controller import TenantRouter
    from app.api.v1.module_platform.video.controller import VideoRouter

    router = APIRouter(prefix="/platform")
    router.include_router(TenantRouter)
    router.include_router(PackageRouter)
    router.include_router(PluginRouter)
    router.include_router(EmailRouter)
    router.include_router(OrderRouter)
    router.include_router(PaymentRouter)
    router.include_router(RefundRouter)
    router.include_router(PlatformInvoiceRouter)
    router.include_router(TenantInvoiceRouter)
    router.include_router(TenantOrderRouter)
    router.include_router(TenantSelfServiceRouter)
    router.include_router(MenuRouter)
    router.include_router(VideoRouter)
    return router
