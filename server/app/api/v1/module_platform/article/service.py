"""文章服务：CRUD + 数据范围过滤。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_platform.article.model import ArticleModel
from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.data_scope import apply_data_scope, load_user_dept_id
from app.core.exceptions import CustomException

_UPDATE_FIELDS = (
    "title",
    "category_id",
    "author",
    "image",
    "describe",
    "content",
    "is_link",
    "link_url",
    "is_hot",
    "sort",
    "status",
    "summary",
    "cover_image",
    "category",
    "tags",
)


class ArticleService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    async def _scoped(self, q):
        q = q.where(not_deleted(ArticleModel))
        return await apply_data_scope(q, ArticleModel, self.auth)

    async def _get(self, article_id: int) -> ArticleModel | None:
        q = await self._scoped(select(ArticleModel).where(ArticleModel.id == article_id))
        return (await self.db.execute(q)).scalar_one_or_none()

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = await self._scoped(select(ArticleModel))
        title = (params.get("title") or "").strip()
        if title:
            q = q.where(ArticleModel.title.like(f"%{title}%"))
        author = (params.get("author") or "").strip()
        if author:
            q = q.where(ArticleModel.author.like(f"%{author}%"))
        if params.get("status") not in (None, ""):
            q = q.where(ArticleModel.status == int(params["status"]))

        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(
            q.order_by(ArticleModel.sort.asc(), ArticleModel.id.desc()).offset((page - 1) * limit).limit(limit)
        )
        rows = [row_to_dict(x) for x in result.scalars().all()]
        return page_result(rows, total, page, limit)

    async def get_detail(self, article_id: int) -> dict[str, Any] | None:
        obj = await self._get(article_id)
        return row_to_dict(obj) if obj else None

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        tid = int(self.auth.tenant_id or 0)
        if tid <= 0:
            raise CustomException(msg="缺少租户信息", code=400)
        obj = ArticleModel(
            title=data["title"],
            category_id=int(data["category_id"]),
            author=data.get("author"),
            image=data.get("image") or "",
            describe=data["describe"],
            content=data.get("content") or "",
            is_link=int(data.get("is_link") or 2),
            link_url=data.get("link_url"),
            is_hot=int(data.get("is_hot") or 2),
            sort=int(data.get("sort") if data.get("sort") is not None else 100),
            status=int(data.get("status") if data.get("status") is not None else 1),
            summary=data.get("summary"),
            cover_image=data.get("cover_image"),
            category=data.get("category"),
            tags=data.get("tags"),
            views=0,
            tenant_id=tid,
            dept_id=await load_user_dept_id(self.auth),
            created_by=operator,
            updated_by=operator,
        )
        self.db.add(obj)
        await self.db.flush()
        return row_to_dict(obj)

    async def update(self, article_id: int, data: dict[str, Any], operator: int) -> dict[str, Any]:
        obj = await self._get(article_id)
        if not obj:
            raise CustomException(msg="文章不存在", code=404)
        for field in _UPDATE_FIELDS:
            if field in data:
                setattr(obj, field, data[field])
        obj.updated_by = operator
        await self.db.flush()
        return row_to_dict(obj)

    async def delete(self, ids: list[int]) -> int:
        if not ids:
            return 0
        now = datetime.now()
        count = 0
        for article_id in ids:
            obj = await self._get(int(article_id))
            if not obj:
                continue
            obj.delete_time = now
            count += 1
        await self.db.flush()
        return count

    async def update_status(self, article_id: int, status: int) -> None:
        obj = await self._get(article_id)
        if not obj:
            raise CustomException(msg="文章不存在", code=404)
        obj.status = status
        await self.db.flush()
