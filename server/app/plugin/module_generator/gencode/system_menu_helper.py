"""代码生成写 sa_system_menu（替代已移除的 platform_menu）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.module_system.common import not_deleted
from app.api.v1.module_system.menu.model import MenuModel
from app.common.enums import QueueEnum
from app.core.base_schema import AuthSchema


class GenMenuCreate(BaseModel):
    name: str
    type: int
    order: int = 9999
    permission: str | None = None
    icon: str | None = "menu"
    route_name: str | None = None
    route_path: str | None = None
    component_path: str | None = None
    redirect: str | None = None
    hidden: bool = False
    keep_alive: bool = True
    parent_id: int | None = None
    status: int | str = 1
    description: str | None = None


def _yes_no(flag: bool) -> int:
    return 1 if flag else 2


def _map_status(v: int | str) -> int:
    # platform_menu: 0=启用 → sa_system_menu: 1=启用
    if str(v) == "0":
        return 1
    if str(v) == "1":
        return 0
    return int(v or 1)


def _to_menu_fields(data: GenMenuCreate, operator: int) -> dict[str, Any]:
    code = (data.permission or data.route_name or data.name or "").strip() or None
    return {
        "parent_id": int(data.parent_id or 0),
        "name": data.name,
        "code": code,
        "slug": code,
        "type": data.type,
        "path": data.route_path,
        "component": data.component_path,
        "icon": data.icon,
        "sort": data.order,
        "link_url": data.redirect if data.type == 4 else None,
        "is_hidden": _yes_no(data.hidden),
        "is_keep_alive": _yes_no(data.keep_alive),
        "status": _map_status(data.status),
        "remark": data.description,
        "created_by": operator,
        "updated_by": operator,
    }


@dataclass
class _MenuRow:
    id: int
    type: int
    name: str
    route_path: str | None = None


class GenMenuCRUD:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db = auth.db

    def _row(self, m: MenuModel) -> _MenuRow:
        return _MenuRow(id=int(m.id), type=int(m.type), name=m.name or "", route_path=m.path)

    async def get(self, **kwargs: Any) -> _MenuRow | None:
        q = select(MenuModel).where(not_deleted(MenuModel))
        parent_id = kwargs.get("parent_id")
        if parent_id is not None:
            if isinstance(parent_id, tuple) and parent_id[0] == QueueEnum.none.value:
                q = q.where(MenuModel.parent_id == 0)
            else:
                q = q.where(MenuModel.parent_id == int(parent_id or 0))
        if "name" in kwargs:
            q = q.where(MenuModel.name == kwargs["name"])
        if "type" in kwargs:
            q = q.where(MenuModel.type == kwargs["type"])
        if "permission" in kwargs and kwargs["permission"]:
            perm = kwargs["permission"]
            q = q.where((MenuModel.code == perm) | (MenuModel.slug == perm))
        result = await self.db.execute(q.limit(1))
        m = result.scalar_one_or_none()
        return self._row(m) if m else None

    async def create(self, data: GenMenuCreate) -> _MenuRow:
        operator = int(getattr(self.auth.user, "id", 0) or 0)
        fields = _to_menu_fields(data, operator)
        obj = MenuModel(**fields)
        self.db.add(obj)
        await self.db.flush()
        return self._row(obj)
