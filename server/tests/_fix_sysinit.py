from pathlib import Path

text = '''"""system 包 — 避免在 __init__ 中导入 controller，防止与 dependencies 循环依赖。"""

__all__ = ["system_router", "CoreRouter"]


def __getattr__(name: str):
    if name == "system_router":
        from fastapi import APIRouter

        from app.api.v1.module_system.auth.controller import AuthRouter
        from app.api.v1.module_system.dept.controller import DeptRouter
        from app.api.v1.module_system.menu.controller import MenuRouter
        from app.api.v1.module_system.role.controller import RoleRouter
        from app.api.v1.module_system.tenant.controller import TenantRouter
        from app.api.v1.module_system.user.controller import UserRouter

        router = APIRouter(prefix="/system")
        router.include_router(AuthRouter)
        router.include_router(DeptRouter)
        router.include_router(MenuRouter)
        router.include_router(RoleRouter)
        router.include_router(TenantRouter)
        router.include_router(UserRouter)
        return router
    if name == "CoreRouter":
        from app.api.v1.module_system.auth.controller import CoreRouter

        return CoreRouter
    raise AttributeError(name)
'''

# fix paren
text = text.replace(
    'router = APIRouter(prefix="/system")\n',
    'router = APIRouter(prefix=' + repr('/system') + ')\n',
)
Path('app/api/v1/module_system/__init__.py').write_text(text, encoding='utf-8')
for line in Path('app/api/v1/module_system/__init__.py').read_text(encoding='utf-8').splitlines():
    if 'APIRouter' in line:
        print(repr(line), line.endswith(')'))
