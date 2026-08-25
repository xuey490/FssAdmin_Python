"""部门服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import build_tree, not_deleted, row_to_dict, status_text
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException


class DeptService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    def _tenant_filter(self, q):
        tid = int(self.auth.tenant_id or 0)
        user = self.auth.user
        if user and int(getattr(user, "is_super", 0) or 0) == 1:
            # 超管仍按当前租户看业务数据（对齐 phpserver 列表隔离）
            if tid > 0:
                return q.where(DeptModel.tenant_id == tid)
            return q
        return q.where(DeptModel.tenant_id == tid)

    async def _load_leaders(self, leader_ids: list[int]) -> dict[int, dict[str, Any]]:
        ids = [int(x) for x in leader_ids if x]
        if not ids:
            return {}
        result = await self.db.execute(
            select(UserModel).where(UserModel.id.in_(ids), not_deleted(UserModel))
        )
        out: dict[int, dict[str, Any]] = {}
        for u in result.scalars().all():
            out[int(u.id)] = {
                "id": u.id,
                "username": u.username,
                "realname": u.realname,
                "phone": u.phone,
                "email": u.email,
                "avatar": u.avatar,
                "status": u.status,
            }
        return out

    def _attach_leader(self, item: dict[str, Any], leaders: dict[int, dict[str, Any]]) -> None:
        lid = int(item.get("leader_id") or 0)
        leader = leaders.get(lid) if lid else None
        item["leader"] = leader
        item["leader_name"] = (leader.get("realname") or leader.get("username")) if leader else None

    async def _rows(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = params or {}
        q = select(DeptModel).where(not_deleted(DeptModel)).order_by(DeptModel.sort.asc(), DeptModel.id.asc())
        q = self._tenant_filter(q)
        if params.get("name") or params.get("dept_name"):
            q = q.where(DeptModel.name.like(f"%{params.get('name') or params.get('dept_name')}%"))
        if params.get("code") or params.get("dept_code"):
            q = q.where(DeptModel.code.like(f"%{params.get('code') or params.get('dept_code')}%"))
        if params.get("status") not in (None, ""):
            st = int(params["status"])
            if st == 2:
                st = 0
            q = q.where(DeptModel.status == st)
        result = await self.db.execute(q)
        depts = list(result.scalars().all())
        leaders = await self._load_leaders([int(d.leader_id or 0) for d in depts])
        rows = []
        for d in depts:
            item = row_to_dict(d)
            item["status_text"] = status_text(d.status)
            # 对齐前端 ElTree / ElTreeSelect
            item["label"] = d.name
            item["value"] = d.id
            item["name"] = d.name
            self._attach_leader(item, leaders)
            rows.append(item)
        return rows

    async def get_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return build_tree(await self._rows(params), promote_orphans=True)

    async def get_tree(self) -> list[dict[str, Any]]:
        return await self.get_list({})

    async def get_all_enabled(self) -> list[dict[str, Any]]:
        rows = await self._rows({"status": 1})
        return rows

    async def get_access_dept(self) -> list[dict[str, Any]]:
        return build_tree(await self._rows({"status": 1}), promote_orphans=True)

    async def get_detail(self, dept_id: int) -> dict[str, Any] | None:
        result = await self.db.execute(select(DeptModel).where(DeptModel.id == dept_id, not_deleted(DeptModel)))
        d = result.scalar_one_or_none()
        if not d:
            return None
        item = row_to_dict(d)
        leaders = await self._load_leaders([int(d.leader_id or 0)])
        self._attach_leader(item, leaders)
        return item

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        parent_id = int(data.get("parent_id") or 0)
        level = "0,"
        if parent_id:
            pq = await self.db.execute(select(DeptModel).where(DeptModel.id == parent_id))
            parent = pq.scalar_one_or_none()
            if parent:
                level = f"{parent.level or '0,'}{parent.id},"
        obj = DeptModel(
            parent_id=parent_id,
            name=data.get("name"),
            code=data.get("code"),
            leader_id=data.get("leader_id"),
            level=level,
            tenant_id=int(self.auth.tenant_id or 0),
            sort=int(data.get("sort") or 0),
            status=int(data.get("status", 1)),
            remark=data.get("remark"),
            created_by=operator,
            updated_by=operator,
        )
        self.db.add(obj)
        await self.db.flush()
        return row_to_dict(obj)

    async def update(self, dept_id: int, data: dict[str, Any], operator: int) -> dict[str, Any]:
        result = await self.db.execute(select(DeptModel).where(DeptModel.id == dept_id, not_deleted(DeptModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="部门不存在", code=404)
        for field in ("name", "code", "leader_id", "sort", "status", "remark", "parent_id"):
            if field in data:
                setattr(obj, field, data[field])
        obj.updated_by = operator
        await self.db.flush()
        return row_to_dict(obj)

    async def delete(self, dept_id: int) -> bool:
        result = await self.db.execute(select(DeptModel).where(DeptModel.id == dept_id, not_deleted(DeptModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def update_status(self, dept_id: int, status: int) -> bool:
        result = await self.db.execute(select(DeptModel).where(DeptModel.id == dept_id, not_deleted(DeptModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.status = status
        await self.db.flush()
        return True

    async def get_children_ids(self, dept_id: int) -> list[int]:
        result = await self.db.execute(select(DeptModel).where(not_deleted(DeptModel)))
        all_depts = list(result.scalars().all())
        children: list[int] = []

        def walk(pid: int) -> None:
            for d in all_depts:
                if int(d.parent_id or 0) == pid:
                    children.append(d.id)
                    walk(d.id)

        walk(dept_id)
        return children
