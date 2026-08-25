"""角色服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import build_tree, not_deleted, parse_page, row_to_dict, status_text
from app.api.v1.module_system.menu.service import MenuService
from app.api.v1.module_system.role.model import RoleDeptModel, RoleMenuModel, RoleModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException


class RoleService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    @property
    def tenant_id(self) -> int:
        return int(self.auth.tenant_id or 0)

    def _scoped(self, q):
        return q.where(RoleModel.tenant_id == self.tenant_id)

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(RoleModel).where(not_deleted(RoleModel))
        q = self._scoped(q)
        if params.get("name"):
            q = q.where(RoleModel.name.like(f"%{params['name']}%"))
        if params.get("code"):
            q = q.where(RoleModel.code.like(f"%{params['code']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(RoleModel.status == int(params["status"]))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(q.order_by(RoleModel.sort.asc(), RoleModel.id.asc()).offset((page - 1) * limit).limit(limit))
        rows = []
        for r in result.scalars().all():
            item = row_to_dict(r)
            item["status_text"] = status_text(r.status)
            rows.append(item)
        return page_result(rows, total, page, limit)

    async def get_all(self) -> list[dict[str, Any]]:
        q = select(RoleModel).where(not_deleted(RoleModel), RoleModel.status == 1)
        q = self._scoped(q)
        result = await self.db.execute(q.order_by(RoleModel.sort.asc()))
        return [row_to_dict(r) for r in result.scalars().all()]

    async def get_access_role(self) -> list[dict[str, Any]]:
        return [{"id": r["id"], "name": r["name"]} for r in await self.get_all()]

    async def get_tree(self) -> list[dict[str, Any]]:
        rows = await self.get_all()
        for r in rows:
            r["label"] = r.get("name")
        return build_tree(rows)

    async def get_detail(self, role_id: int) -> dict[str, Any] | None:
        result = await self.db.execute(select(RoleModel).where(RoleModel.id == role_id, not_deleted(RoleModel)))
        role = result.scalar_one_or_none()
        if not role:
            return None
        d = row_to_dict(role)
        mq = await self.db.execute(
            select(RoleMenuModel.menu_id).where(RoleMenuModel.role_id == role_id)
        )
        d["menu_ids"] = list(mq.scalars().all())
        dq = await self.db.execute(select(RoleDeptModel.dept_id).where(RoleDeptModel.role_id == role_id))
        d["dept_ids"] = list(dq.scalars().all())
        return d

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        obj = RoleModel(
            parent_id=int(data.get("parent_id") or 0),
            name=data.get("name"),
            code=data.get("code"),
            level=int(data.get("level") or 1),
            data_scope=int(data.get("data_scope") or 1),
            sort=int(data.get("sort") or 100),
            status=int(data.get("status", 1)),
            remark=data.get("remark"),
            tenant_id=self.tenant_id,
            created_by=operator,
            updated_by=operator,
        )
        self.db.add(obj)
        await self.db.flush()
        if data.get("dept_ids") is not None:
            await self._sync_depts(obj.id, data.get("dept_ids") or [], operator)
        return row_to_dict(obj)

    async def update(self, role_id: int, data: dict[str, Any], operator: int) -> dict[str, Any]:
        if role_id == 1:
            raise CustomException(msg="系统角色不可修改", code=403)
        result = await self.db.execute(select(RoleModel).where(RoleModel.id == role_id, not_deleted(RoleModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="角色不存在", code=404)
        for field in ("name", "code", "level", "data_scope", "sort", "status", "remark", "parent_id"):
            if field in data:
                setattr(obj, field, data[field])
        obj.updated_by = operator
        if "dept_ids" in data:
            await self._sync_depts(role_id, data.get("dept_ids") or [], operator)
        await self.db.flush()
        return row_to_dict(obj)

    async def delete(self, role_id: int) -> bool:
        if role_id == 1:
            raise CustomException(msg="系统角色不可删除", code=403)
        result = await self.db.execute(select(RoleModel).where(RoleModel.id == role_id, not_deleted(RoleModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def update_status(self, role_id: int, status: int) -> bool:
        result = await self.db.execute(select(RoleModel).where(RoleModel.id == role_id, not_deleted(RoleModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.status = status
        await self.db.flush()
        return True

    async def _sync_depts(self, role_id: int, dept_ids: list[int], operator: int) -> None:
        old = await self.db.execute(select(RoleDeptModel).where(RoleDeptModel.role_id == role_id))
        for row in old.scalars().all():
            await self.db.delete(row)
        for did in dept_ids:
            self.db.add(RoleDeptModel(role_id=role_id, dept_id=int(did)))
        await self.db.flush()

    async def assign_menus(self, role_id: int, menu_ids: list[int], operator: int) -> bool:
        menu_svc = MenuService(self.auth)
        menu_ids = await menu_svc.expand_with_parent_ids([int(x) for x in menu_ids])
        old = await self.db.execute(select(RoleMenuModel).where(RoleMenuModel.role_id == role_id))
        for row in old.scalars().all():
            await self.db.delete(row)
        for mid in menu_ids:
            self.db.add(RoleMenuModel(role_id=role_id, menu_id=mid))
        await self.db.flush()
        return True

    async def menu_by_role(self, role_id: int) -> dict[str, Any]:
        q = await self.db.execute(
            select(RoleMenuModel.menu_id).where(RoleMenuModel.role_id == role_id)
        )
        return {"menus": [{"id": mid} for mid in q.scalars().all()]}
