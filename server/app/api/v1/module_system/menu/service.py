"""菜单与权限解析（对齐 phpserver SysUser::getMergedMenuIds / getMenuTree / SysMenuService）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import build_tree, not_deleted, row_to_dict, status_text
from app.api.v1.module_system.menu.model import MenuModel
from app.api.v1.module_system.role.model import RoleMenuModel
from app.api.v1.module_system.user.model import UserMenuModel, UserModel, UserRoleModel
from app.core.base_schema import AuthSchema

# 1目录 2菜单 3按钮 4外链 — 导航树不含按钮
_NAV_TYPES = (1, 2, 4)
_TYPE_NAME = {1: "目录", 2: "菜单", 3: "按钮", 4: "外链"}


def _format_menu(m: MenuModel | dict[str, Any]) -> dict[str, Any]:
    d = row_to_dict(m) if not isinstance(m, dict) else dict(m)
    d["status_text"] = status_text(d.get("status"))
    d["visible_text"] = "隐藏" if int(d.get("is_hidden") or 0) == 1 else "显示"
    d["menu_type_name"] = _TYPE_NAME.get(int(d.get("type") or 0), "未知")
    d["value"] = d.get("id")
    d["label"] = d.get("name") or ""
    return d


class MenuService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    def _is_super(self, user: UserModel | None = None) -> bool:
        u = user or self.auth.user
        return bool(u and int(getattr(u, "is_super", 0) or 0) == 1)

    async def _all_menus(self) -> list[MenuModel]:
        result = await self.db.execute(
            select(MenuModel)
            .where(not_deleted(MenuModel), MenuModel.status == 1)
            .order_by(MenuModel.sort.asc(), MenuModel.id.asc())
        )
        return list(result.scalars().all())

    async def expand_with_parent_ids(self, menu_ids: list[int]) -> list[int]:
        if not menu_ids:
            return []
        result = await self.db.execute(select(MenuModel).where(not_deleted(MenuModel)))
        by_id = {m.id: m for m in result.scalars().all()}
        out = set(int(x) for x in menu_ids)
        for mid in list(out):
            cur = by_id.get(mid)
            while cur and int(cur.parent_id or 0) > 0:
                pid = int(cur.parent_id)
                if pid in out:
                    break
                out.add(pid)
                cur = by_id.get(pid)
        return sorted(out)

    async def get_merged_menu_ids(self, user_id: int, tenant_id: int | None = None) -> list[int]:
        """角色菜单 ∪ 个人菜单；超管=全部启用菜单。"""
        tid = int(tenant_id if tenant_id is not None else (self.auth.tenant_id or 0))
        user = self.auth.user
        # 查他人菜单时以目标用户为准
        if user is None or int(user.id) != int(user_id):
            uq = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
            user = uq.scalar_one_or_none()

        if self._is_super(user):
            return [m.id for m in await self._all_menus()]

        menu_ids: set[int] = set()
        if tid > 0:
            role_ids = list(
                (
                    await self.db.execute(
                        select(UserRoleModel.role_id).where(
                            UserRoleModel.user_id == user_id,
                            UserRoleModel.tenant_id == tid,
                            not_deleted(UserRoleModel),
                        )
                    )
                ).scalars().all()
            )
            if role_ids:
                rm = await self.db.execute(
                    select(RoleMenuModel.menu_id).where(RoleMenuModel.role_id.in_(role_ids))
                )
                menu_ids.update(int(x) for x in rm.scalars().all())

            um = await self.db.execute(
                select(UserMenuModel.menu_id).where(
                    UserMenuModel.user_id == user_id,
                    UserMenuModel.tenant_id == tid,
                    not_deleted(UserMenuModel),
                )
            )
            menu_ids.update(int(x) for x in um.scalars().all())

        return sorted(menu_ids)

    async def get_user_menu_tree(self, user_id: int | None = None) -> list[dict[str, Any]]:
        """左侧导航：目录/菜单/外链；补全祖先；严格建树（对齐 phpserver）。"""
        uid = int(user_id or self.auth.user.id)
        user = self.auth.user
        menu_ids = await self.get_merged_menu_ids(uid)
        if not menu_ids:
            return []
        if not self._is_super(user if user and int(user.id) == uid else None):
            menu_ids = await self.expand_with_parent_ids(menu_ids)

        result = await self.db.execute(
            select(MenuModel)
            .where(
                not_deleted(MenuModel),
                MenuModel.id.in_(menu_ids),
                MenuModel.status == 1,
                MenuModel.type.in_(_NAV_TYPES),
            )
            .order_by(MenuModel.sort.asc(), MenuModel.id.asc())
        )
        rows = [_format_menu(m) for m in result.scalars().all()]
        return build_tree(rows, promote_orphans=False)

    async def get_user_permissions(self, user_id: int | None = None) -> list[str]:
        uid = int(user_id or self.auth.user.id)
        if self._is_super():
            return ["*"]
        menu_ids = await self.get_merged_menu_ids(uid)
        if not menu_ids:
            return []
        result = await self.db.execute(
            select(MenuModel.slug).where(
                not_deleted(MenuModel),
                MenuModel.id.in_(menu_ids),
                MenuModel.status == 1,
                MenuModel.slug.isnot(None),
                MenuModel.slug != "",
            )
        )
        return sorted({s for s in result.scalars().all() if s})

    async def get_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """菜单管理列表：全量严格树（对齐 SysMenuService.getList）。"""
        q = select(MenuModel).where(not_deleted(MenuModel)).order_by(MenuModel.sort.asc(), MenuModel.id.asc())
        result = await self.db.execute(q)
        rows = [_format_menu(m) for m in result.scalars().all()]
        tree = build_tree(rows, promote_orphans=False)

        name = (params.get("name") or "").strip()
        path = (params.get("path") or "").strip()
        status = params.get("status")
        if not name and not path and status in (None, ""):
            return tree
        return self._filter_tree(tree, name, path, status)

    def _filter_tree(
        self, tree: list[dict[str, Any]], name: str, path: str, status: Any
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in tree:
            kids = self._filter_tree(item.get("children") or [], name, path, status)
            name_ok = not name or name.lower() in str(item.get("name") or "").lower()
            path_ok = not path or path.lower() in str(item.get("path") or "").lower()
            status_ok = status in (None, "") or str(item.get("status")) == str(status)
            if (name_ok and path_ok and status_ok) or kids:
                node = dict(item)
                if kids:
                    node["children"] = kids
                else:
                    node.pop("children", None)
                out.append(node)
        return out

    async def get_tree(self) -> list[dict[str, Any]]:
        return await self.get_list({})

    async def get_detail(self, menu_id: int) -> dict[str, Any] | None:
        result = await self.db.execute(select(MenuModel).where(MenuModel.id == menu_id, not_deleted(MenuModel)))
        m = result.scalar_one_or_none()
        return _format_menu(m) if m else None

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        obj = MenuModel(**{k: v for k, v in data.items() if hasattr(MenuModel, k) and k != "id"})
        obj.created_by = operator
        obj.updated_by = operator
        self.db.add(obj)
        await self.db.flush()
        return _format_menu(obj)

    async def update(self, menu_id: int, data: dict[str, Any], operator: int) -> dict[str, Any] | None:
        result = await self.db.execute(select(MenuModel).where(MenuModel.id == menu_id, not_deleted(MenuModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for k, v in data.items():
            if k in ("id", "create_time", "delete_time"):
                continue
            if hasattr(obj, k):
                setattr(obj, k, v)
        obj.updated_by = operator
        await self.db.flush()
        return _format_menu(obj)

    async def delete(self, menu_id: int) -> bool:
        from datetime import datetime

        result = await self.db.execute(select(MenuModel).where(MenuModel.id == menu_id, not_deleted(MenuModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def update_status(self, menu_id: int, status: int) -> bool:
        result = await self.db.execute(select(MenuModel).where(MenuModel.id == menu_id, not_deleted(MenuModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.status = status
        await self.db.flush()
        return True

    async def get_assignable_tree(self) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(MenuModel).where(not_deleted(MenuModel), MenuModel.status == 1).order_by(MenuModel.sort.asc())
        )
        rows = [
            {
                "id": m.id,
                "value": m.id,
                "label": m.name,
                "name": m.name,
                "type": m.type,
                "parent_id": int(m.parent_id or 0),
            }
            for m in result.scalars().all()
        ]
        return build_tree(rows, promote_orphans=False)

    async def get_access_menu(self) -> list[dict[str, Any]]:
        return await self.get_assignable_tree()

    async def get_permission_tree(self) -> list[dict[str, Any]]:
        return await self.get_assignable_tree()
