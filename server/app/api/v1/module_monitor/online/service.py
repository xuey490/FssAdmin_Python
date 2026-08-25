"""在线用户服务 — 对齐 web `/api/monitor/online/*` 与 server1 OnlineService。"""

from __future__ import annotations

from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserDeptModel
from app.core.logger import logger
from app.core.token_manager import build_token_manager

from .schema import OnlineQueryParam


def _pick(session: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = session.get(k)
        if v is not None and str(v).strip() != "":
            return str(v)
    return default


def session_to_row(session: dict[str, Any]) -> dict[str, Any]:
    """内部会话字典 → 前端 Online 行。"""
    return {
        "tokenId": _pick(session, "tokenId", "session_id", "jti"),
        "userName": _pick(session, "userName", "user_name", "username"),
        "deptName": _pick(session, "deptName", "dept_name"),
        "ipaddr": _pick(session, "ipaddr", "ip", "loginIp"),
        "loginLocation": _pick(session, "loginLocation", "login_location"),
        "os": _pick(session, "os"),
        "browser": _pick(session, "browser"),
        "loginTime": _pick(session, "loginTime", "login_time"),
        # 内部补全用
        "_user_id": int(session.get("user_id") or session.get("userId") or 0),
        "_tenant_id": int(session.get("tenant_id") or session.get("tenantId") or 0),
    }


class OnlineService:
    @staticmethod
    async def get_online_list(
        redis: Redis,
        search: OnlineQueryParam | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        sessions = await build_token_manager(redis).list_sessions()
        rows = [session_to_row(s) for s in sessions if s]

        class _Q:
            user_name = ""
            ipaddr = ""
            order_field = "loginTime"
            order_type = "desc"
            page = 1
            limit = 10

        q = search or _Q()
        if q.user_name:
            kw = q.user_name.lower()
            rows = [r for r in rows if kw in r["userName"].lower()]
        if q.ipaddr:
            kw = q.ipaddr
            rows = [r for r in rows if kw in r["ipaddr"]]

        # 补全缺失部门名
        if db is not None:
            await OnlineService._fill_dept_names(db, rows)

        reverse = q.order_type != "asc"
        field_map = {
            "loginTime": "loginTime",
            "login_time": "loginTime",
            "userName": "userName",
            "ipaddr": "ipaddr",
        }
        sort_key = field_map.get(q.order_field, "loginTime")
        rows.sort(key=lambda r: r.get(sort_key) or "", reverse=reverse)

        total = len(rows)
        page = max(1, q.page)
        limit = max(1, q.limit)
        start = (page - 1) * limit
        page_rows = rows[start : start + limit]

        # 去掉内部字段
        list_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in page_rows]
        return {
            "list": list_rows,
            "data": list_rows,
            "total": total,
            "page": page,
            "current_page": page,
            "limit": limit,
            "per_page": limit,
            "size": limit,
        }

    @staticmethod
    async def _fill_dept_names(db: AsyncSession, rows: list[dict[str, Any]]) -> None:
        need = [r for r in rows if not r.get("deptName") and r.get("_user_id")]
        if not need:
            return
        # 按 (user_id, tenant_id) 批量查
        user_ids = list({int(r["_user_id"]) for r in need})
        result = await db.execute(
            select(UserDeptModel.user_id, UserDeptModel.tenant_id, UserDeptModel.dept_id).where(
                UserDeptModel.user_id.in_(user_ids)
            )
        )
        links = result.all()
        if not links:
            # 回退 user.dept_id
            from app.api.v1.module_system.user.model import UserModel

            uq = await db.execute(
                select(UserModel.id, UserModel.dept_id).where(
                    UserModel.id.in_(user_ids), not_deleted(UserModel)
                )
            )
            user_depts = [(int(uid), int(did)) for uid, did in uq.all() if did]
            dept_ids = {did for _, did in user_depts}
            depts: dict[int, str] = {}
            if dept_ids:
                dq = await db.execute(
                    select(DeptModel.id, DeptModel.name).where(
                        DeptModel.id.in_(dept_ids), not_deleted(DeptModel)
                    )
                )
                depts = {int(i): str(n or "") for i, n in dq.all()}
            uid_dept = {uid: depts.get(did, "") for uid, did in user_depts}
            for r in need:
                r["deptName"] = uid_dept.get(int(r["_user_id"]), "") or ""
            return

        dept_ids = list({int(x.dept_id) for x in links if x.dept_id})
        depts: dict[int, str] = {}
        if dept_ids:
            dq = await db.execute(
                select(DeptModel.id, DeptModel.name).where(
                    DeptModel.id.in_(dept_ids), not_deleted(DeptModel)
                )
            )
            depts = {int(i): str(n or "") for i, n in dq.all()}

        # tenant 优先匹配
        by_ut: dict[tuple[int, int], str] = {}
        by_u: dict[int, str] = {}
        for uid, tid, did in links:
            name = depts.get(int(did), "")
            by_ut[(int(uid), int(tid or 0))] = name
            by_u.setdefault(int(uid), name)
        for r in need:
            tid = int(r.get("_tenant_id") or 0)
            r["deptName"] = by_ut.get((int(r["_user_id"]), tid)) or by_u.get(int(r["_user_id"]), "") or ""

    @staticmethod
    async def delete_online(redis: Redis, session_id: str) -> None:
        await build_token_manager(redis).delete_session(session_id)
        logger.info("强制下线用户会话: {}", session_id)

    @staticmethod
    async def clear_online(redis: Redis) -> None:
        tm = build_token_manager(redis)
        for s in await tm.list_sessions():
            sid = s.get("tokenId") or s.get("session_id")
            if sid:
                await tm.delete_session(str(sid))
        logger.info("清除所有在线用户会话成功")
