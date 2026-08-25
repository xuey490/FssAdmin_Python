"""邮件日志服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict
from app.api.v1.module_system.email_log.model import MailLogModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema


class EmailLogService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db = auth.db  # type: ignore[assignment]

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(MailLogModel).where(not_deleted(MailLogModel))
        if params.get("from"):
            q = q.where(MailLogModel.from_.like(f"%{params['from']}%"))
        if params.get("email"):
            q = q.where(MailLogModel.email.like(f"%{params['email']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(MailLogModel.status == params["status"])
        create_time = params.get("create_time")
        if isinstance(create_time, list) and len(create_time) >= 2:
            if create_time[0]:
                q = q.where(MailLogModel.create_time >= create_time[0])
            if create_time[1]:
                q = q.where(MailLogModel.create_time <= create_time[1])
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (
            await self.db.execute(
                q.order_by(MailLogModel.create_time.desc(), MailLogModel.id.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).scalars().all()
        return page_result([row_to_dict(r) for r in rows], total, page, limit)

    async def destroy(self, ids: list[int]) -> int:
        count = 0
        now = datetime.now()
        for eid in ids:
            obj = await self.db.get(MailLogModel, eid)
            if obj and not obj.delete_time:
                obj.delete_time = now
                count += 1
        await self.db.flush()
        return count
