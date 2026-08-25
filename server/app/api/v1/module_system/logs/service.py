"""登录/操作日志服务（对齐 phpserver LogController）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict
from app.api.v1.module_system.logs.model import LoginLogModel, OperLogModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema


class LogService:
    def __init__(self, auth: AuthSchema | None = None, db: AsyncSession | None = None) -> None:
        self.auth = auth
        self.db: AsyncSession = (auth.db if auth else db)  # type: ignore[assignment]

    async def login_page(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(LoginLogModel).where(not_deleted(LoginLogModel))
        if params.get("username"):
            q = q.where(LoginLogModel.username.like(f"%{params['username']}%"))
        if params.get("ip"):
            q = q.where(LoginLogModel.ip.like(f"%{params['ip']}%"))
        status = params.get("status") if params.get("status") not in (None, "") else params.get("login_status")
        if status not in (None, ""):
            q = q.where(LoginLogModel.status == int(status))
        login_time = params.get("login_time")
        if isinstance(login_time, list) and len(login_time) >= 2:
            if login_time[0]:
                q = q.where(LoginLogModel.login_time >= login_time[0])
            if login_time[1]:
                q = q.where(LoginLogModel.login_time <= login_time[1])
        elif params.get("start_time"):
            q = q.where(LoginLogModel.login_time >= params["start_time"])
            if params.get("end_time"):
                q = q.where(LoginLogModel.login_time <= params["end_time"])
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (
            await self.db.execute(
                q.order_by(LoginLogModel.login_time.desc(), LoginLogModel.id.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).scalars().all()
        return page_result([row_to_dict(r) for r in rows], total, page, limit)

    async def delete_login(self, ids: list[int]) -> int:
        if not ids:
            return 0
        result = await self.db.execute(delete(LoginLogModel).where(LoginLogModel.id.in_(ids)))
        await self.db.flush()
        return int(result.rowcount or 0)

    async def oper_page(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(OperLogModel).where(not_deleted(OperLogModel))
        if params.get("username"):
            q = q.where(OperLogModel.username.like(f"%{params['username']}%"))
        if params.get("ip"):
            q = q.where(OperLogModel.ip.like(f"%{params['ip']}%"))
        if params.get("service_name"):
            q = q.where(OperLogModel.service_name.like(f"%{params['service_name']}%"))
        if params.get("router"):
            q = q.where(OperLogModel.router.like(f"%{params['router']}%"))
        create_time = params.get("create_time")
        if isinstance(create_time, list) and len(create_time) >= 2:
            if create_time[0]:
                q = q.where(OperLogModel.create_time >= create_time[0])
            if create_time[1]:
                q = q.where(OperLogModel.create_time <= create_time[1])
        elif params.get("start_time"):
            q = q.where(OperLogModel.create_time >= params["start_time"])
            if params.get("end_time"):
                q = q.where(OperLogModel.create_time <= params["end_time"])
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (
            await self.db.execute(
                q.order_by(OperLogModel.create_time.desc(), OperLogModel.id.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).scalars().all()
        return page_result([row_to_dict(r) for r in rows], total, page, limit)

    async def delete_oper(self, ids: list[int]) -> int:
        if not ids:
            return 0
        result = await self.db.execute(delete(OperLogModel).where(OperLogModel.id.in_(ids)))
        await self.db.flush()
        return int(result.rowcount or 0)

    @staticmethod
    async def write_login(
        db: AsyncSession,
        *,
        username: str,
        ip: str = "",
        status: int = 1,
        message: str = "",
        os: str = "",
        browser: str = "",
    ) -> None:
        db.add(
            LoginLogModel(
                username=username[:20] if username else "",
                ip=(ip or "")[:45],
                ip_location="",
                os=(os or "")[:50],
                browser=(browser or "")[:50],
                status=status,
                message=(message or "")[:50],
                login_time=datetime.now(),
            )
        )
        await db.flush()

    @staticmethod
    async def write_oper(
        db: AsyncSession,
        *,
        username: str = "",
        method: str = "",
        router: str = "",
        service_name: str = "",
        ip: str = "",
        request_data: str = "",
        duration: str = "",
        created_by: int | None = None,
    ) -> None:
        db.add(
            OperLogModel(
                username=(username or "")[:20],
                app="system",
                method=(method or "")[:20],
                router=(router or "")[:500],
                service_name=(service_name or "")[:30],
                ip=(ip or "")[:45],
                ip_location="",
                request_data=request_data[:2000] if request_data else "",
                duration=str(duration)[:20],
                created_by=created_by,
            )
        )
        await db.flush()
