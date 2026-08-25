"""岗位服务（对齐 phpserver SysPostService）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict, status_text
from app.api.v1.module_system.post.model import PostModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException


class PostService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    @property
    def tenant_id(self) -> int:
        return int(self.auth.tenant_id or 0)

    def _scoped(self, q):
        return q.where(PostModel.tenant_id == self.tenant_id)

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(PostModel).where(not_deleted(PostModel))
        q = self._scoped(q)
        if params.get("code"):
            q = q.where(PostModel.code.like(f"%{params['code']}%"))
        if params.get("name"):
            q = q.where(PostModel.name.like(f"%{params['name']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(PostModel.status == int(params["status"]))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(
            q.order_by(PostModel.sort.asc(), PostModel.id.asc()).offset((page - 1) * limit).limit(limit)
        )
        rows = []
        for r in result.scalars().all():
            item = row_to_dict(r)
            item["status_text"] = status_text(r.status)
            rows.append(item)
        return page_result(rows, total, page, limit)

    async def get_detail(self, post_id: int) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(PostModel).where(PostModel.id == post_id, not_deleted(PostModel))
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        d = row_to_dict(obj)
        d["status_text"] = status_text(obj.status)
        return d

    async def get_all_enabled(self) -> list[dict[str, Any]]:
        q = select(PostModel).where(not_deleted(PostModel), PostModel.status == 1)
        q = self._scoped(q)
        result = await self.db.execute(q.order_by(PostModel.sort.asc(), PostModel.id.asc()))
        return [row_to_dict(r) for r in result.scalars().all()]

    async def get_access_post(self) -> list[dict[str, Any]]:
        """用户编辑弹窗下拉：id / name / code。"""
        return [
            {"id": r["id"], "name": r["name"], "code": r.get("code")}
            for r in await self.get_all_enabled()
        ]

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip()
        if not name:
            raise CustomException(msg="岗位名称不能为空")
        if not code:
            raise CustomException(msg="岗位编码不能为空")
        exists = await self.db.execute(
            select(PostModel).where(PostModel.code == code, not_deleted(PostModel), PostModel.tenant_id == self.tenant_id)
        )
        if exists.scalar_one_or_none():
            raise CustomException(msg="岗位编码已存在")
        obj = PostModel(
            name=name,
            code=code,
            sort=int(data.get("sort") or 0),
            status=int(data.get("status") if data.get("status") is not None else 1),
            remark=data.get("remark") or "",
            tenant_id=self.tenant_id,
            created_by=operator,
            updated_by=operator,
        )
        self.db.add(obj)
        await self.db.flush()
        return {"id": obj.id}

    async def update(self, post_id: int, data: dict[str, Any], operator: int) -> bool:
        result = await self.db.execute(
            select(PostModel).where(PostModel.id == post_id, not_deleted(PostModel))
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="岗位不存在", code=404)
        for k in ("name", "code", "sort", "status", "remark"):
            if k in data and data[k] is not None:
                setattr(obj, k, data[k])
        obj.updated_by = operator
        await self.db.flush()
        return True

    async def delete(self, post_id: int) -> bool:
        result = await self.db.execute(
            select(PostModel).where(PostModel.id == post_id, not_deleted(PostModel))
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def update_status(self, post_id: int, status: int) -> bool:
        result = await self.db.execute(
            select(PostModel).where(PostModel.id == post_id, not_deleted(PostModel))
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.status = status
        await self.db.flush()
        return True
