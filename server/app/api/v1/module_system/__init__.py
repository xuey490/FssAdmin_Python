"""system 包 — 避免在 __init__ 中导入 controller，防止与 dependencies 循环依赖。"""

__all__ = ["system_router", "CoreRouter"]


def __getattr__(name: str):
    if name == "system_router":
        from fastapi import APIRouter

        from app.api.v1.module_system.attachment.controller import (
            AttachmentCategoryRouter,
            AttachmentRouter,
        )
        from app.api.v1.module_system.auth.controller import AuthRouter
        from app.api.v1.module_system.dept.controller import DeptRouter
        from app.api.v1.module_system.dict.controller import DictRouter
        from app.api.v1.module_system.menu.controller import MenuRouter
        from app.api.v1.module_system.post.controller import PostRouter
        from app.api.v1.module_system.role.controller import RoleRouter
        from app.api.v1.module_system.tenant.controller import TenantRouter
        from app.api.v1.module_system.user.controller import UserRouter

        router = APIRouter(prefix="/system")
        router.include_router(AuthRouter)
        router.include_router(DeptRouter)
        router.include_router(MenuRouter)
        router.include_router(PostRouter)
        router.include_router(RoleRouter)
        router.include_router(TenantRouter)
        router.include_router(UserRouter)
        router.include_router(DictRouter)
        router.include_router(AttachmentRouter)
        router.include_router(AttachmentCategoryRouter)
        return router
    if name == "CoreRouter":
        from fastapi import APIRouter

        from app.api.v1.module_system.auth.controller import CoreRouter as AuthCoreRouter
        from app.api.v1.module_system.config.controller import ConfigRouter
        from app.api.v1.module_system.email_log.controller import EmailLogRouter
        from app.api.v1.module_system.logs.controller import LogsRouter

        router = APIRouter()
        router.include_router(AuthCoreRouter)
        router.include_router(ConfigRouter)
        router.include_router(LogsRouter)
        router.include_router(EmailLogRouter)
        return router
    raise AttributeError(name)
