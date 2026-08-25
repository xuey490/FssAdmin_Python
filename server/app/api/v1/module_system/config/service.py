"""配置服务（对齐 phpserver SysConfigService / SysConfigGroupService）。"""

from __future__ import annotations

import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict
from app.api.v1.module_system.config.model import ConfigGroupModel, ConfigModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException


def _decode_select(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _encode_select(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)


class ConfigService:
    def __init__(self, auth: AuthSchema | None = None, db: AsyncSession | None = None) -> None:
        self.auth = auth
        self.db: AsyncSession = (auth.db if auth else db)  # type: ignore[assignment]

    def _operator(self) -> int:
        if self.auth and self.auth.user:
            return int(self.auth.user.id)
        return 0

    async def group_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(ConfigGroupModel).where(not_deleted(ConfigGroupModel))
        if params.get("name"):
            q = q.where(ConfigGroupModel.name.like(f"%{params['name']}%"))
        if params.get("code"):
            q = q.where(ConfigGroupModel.code.like(f"%{params['code']}%"))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (
            await self.db.execute(q.order_by(ConfigGroupModel.id.asc()).offset((page - 1) * limit).limit(limit))
        ).scalars().all()
        return page_result([row_to_dict(r) for r in rows], total, page, limit)

    async def group_save(self, data: dict[str, Any]) -> dict[str, Any]:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip()
        if not name or not code:
            raise CustomException(msg="配置组名称和编码不能为空", code=1)
        op = self._operator()
        obj = ConfigGroupModel(name=name, code=code, remark=data.get("remark"), created_by=op, updated_by=op)
        self.db.add(obj)
        await self.db.flush()
        return {"id": obj.id}

    async def group_update(self, group_id: int, data: dict[str, Any]) -> None:
        obj = await self.db.get(ConfigGroupModel, group_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="配置组不存在", code=1)
        for field in ("name", "code", "remark"):
            if field in data:
                setattr(obj, field, data[field])
        obj.updated_by = self._operator()
        await self.db.flush()

    async def group_delete(self, group_id: int) -> None:
        obj = await self.db.get(ConfigGroupModel, group_id)
        if not obj or obj.delete_time:
            return
        now = datetime.now()
        obj.delete_time = now
        configs = (
            await self.db.execute(
                select(ConfigModel).where(ConfigModel.group_id == group_id, not_deleted(ConfigModel))
            )
        ).scalars().all()
        for c in configs:
            c.delete_time = now
        await self.db.flush()

    async def config_list(self, params: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
        # 前端按 group_id + saiType=all 不分页取全量
        no_page = params.get("group_id") not in (None, "") and "page" not in params
        page, limit = parse_page(params)
        q = select(ConfigModel).where(not_deleted(ConfigModel))
        if params.get("group_id") not in (None, ""):
            q = q.where(ConfigModel.group_id == int(params["group_id"]))
        if params.get("key"):
            q = q.where(ConfigModel.key.like(f"%{params['key']}%"))
        if params.get("name"):
            q = q.where(ConfigModel.name.like(f"%{params['name']}%"))
        q = q.order_by(ConfigModel.sort.asc(), ConfigModel.id.desc())
        if no_page:
            rows = (await self.db.execute(q)).scalars().all()
            items = []
            for r in rows:
                d = row_to_dict(r)
                d["config_select_data"] = _decode_select(r.config_select_data)
                items.append(d)
            return items
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (await self.db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
        items = []
        for r in rows:
            d = row_to_dict(r)
            d["config_select_data"] = _decode_select(r.config_select_data)
            items.append(d)
        return page_result(items, total, page, limit)

    async def config_save(self, data: dict[str, Any]) -> dict[str, Any]:
        key = (data.get("key") or "").strip()
        name = (data.get("name") or "").strip()
        if not key or not name:
            raise CustomException(msg="配置键和配置名称不能为空", code=1)
        op = self._operator()
        obj = ConfigModel(
            group_id=int(data["group_id"]) if data.get("group_id") not in (None, "") else None,
            key=key,
            value=data.get("value"),
            name=name,
            input_type=data.get("input_type"),
            config_select_data=_encode_select(data.get("config_select_data")),
            sort=int(data.get("sort") or 0),
            remark=data.get("remark"),
            created_by=op,
            updated_by=op,
        )
        self.db.add(obj)
        await self.db.flush()
        return {"id": obj.id}

    async def config_update(self, config_id: int, data: dict[str, Any]) -> None:
        obj = await self.db.get(ConfigModel, config_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="配置项不存在", code=1)
        for field in ("group_id", "key", "value", "name", "input_type", "sort", "remark"):
            if field in data:
                setattr(obj, field, data[field])
        if "config_select_data" in data:
            obj.config_select_data = _encode_select(data.get("config_select_data"))
        obj.updated_by = self._operator()
        await self.db.flush()

    async def config_delete(self, ids: list[int]) -> int:
        count = 0
        now = datetime.now()
        for cid in ids:
            obj = await self.db.get(ConfigModel, cid)
            if obj and not obj.delete_time:
                obj.delete_time = now
                count += 1
        await self.db.flush()
        return count

    async def batch_update(self, configs: list[dict[str, Any]]) -> None:
        op = self._operator()
        for item in configs:
            if "id" not in item or "value" not in item:
                continue
            obj = await self.db.get(ConfigModel, int(item["id"]))
            if obj and not obj.delete_time:
                obj.value = item["value"]
                obj.updated_by = op
        await self.db.flush()

    async def get_by_key(self, key: str) -> str:
        row = (
            await self.db.execute(
                select(ConfigModel).where(ConfigModel.key == key, not_deleted(ConfigModel)).limit(1)
            )
        ).scalar_one_or_none()
        return (row.value if row and row.value is not None else "") or ""

    async def test_email(self, data: dict[str, Any]) -> dict[str, Any]:
        to_email = (data.get("email") or data.get("to") or "").strip()
        if not to_email:
            raise CustomException(msg="请填写测试邮箱", code=1)

        cfg_map: dict[str, str] = {}
        rows = (
            await self.db.execute(
                select(ConfigModel).where(ConfigModel.group_id == 3, not_deleted(ConfigModel))
            )
        ).scalars().all()
        for r in rows:
            cfg_map[r.key] = r.value or ""

        host = data.get("smtp_host") or data.get("Host") or cfg_map.get("Host") or ""
        port = int(data.get("smtp_port") or data.get("Port") or cfg_map.get("Port") or 465)
        user = data.get("smtp_user") or data.get("Username") or cfg_map.get("Username") or ""
        password = data.get("smtp_pass") or data.get("Password") or cfg_map.get("Password") or ""
        from_addr = data.get("smtp_from") or data.get("From") or cfg_map.get("From") or user
        secure = (data.get("SMTPSecure") or cfg_map.get("SMTPSecure") or "ssl").lower()

        if not host or not user or not password:
            raise CustomException(msg="邮件配置不完整", code=1)

        msg = MIMEText("FastAdmin 邮件配置测试", "plain", "utf-8")
        msg["Subject"] = "邮件配置测试"
        msg["From"] = from_addr
        msg["To"] = to_email

        try:
            if secure == "ssl":
                with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
                    smtp.login(user, password)
                    smtp.sendmail(from_addr, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(host, port, timeout=15) as smtp:
                    smtp.starttls()
                    smtp.login(user, password)
                    smtp.sendmail(from_addr, [to_email], msg.as_string())
        except Exception as e:
            raise CustomException(msg=f"邮件发送失败: {e}", code=1) from e

        try:
            from app.api.v1.module_system.email_log.model import MailLogModel

            self.db.add(
                MailLogModel(
                    gateway=host,
                    from_=from_addr,
                    email=to_email,
                    code="",
                    content="邮件配置测试",
                    status="success",
                    response="ok",
                )
            )
            await self.db.flush()
        except Exception:
            pass

        return {"success": True, "message": "邮件发送成功"}
