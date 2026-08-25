"""租户服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict, status_text
from app.api.v1.module_system.tenant.model import TenantModel
from app.api.v1.module_system.user.model import UserModel, UserTenantModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException


class TenantService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(TenantModel).where(not_deleted(TenantModel))
        user = self.auth.user
        if not (user and int(getattr(user, "is_super", 0) or 0) == 1):
            tid = int(self.auth.tenant_id or 0)
            q = q.where(TenantModel.id == tid)
        if params.get("tenant_name"):
            q = q.where(TenantModel.tenant_name.like(f"%{params['tenant_name']}%"))
        if params.get("tenant_code"):
            q = q.where(TenantModel.tenant_code.like(f"%{params['tenant_code']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(TenantModel.status == int(params["status"]))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(q.order_by(TenantModel.id.desc()).offset((page - 1) * limit).limit(limit))
        rows = []
        for t in result.scalars().all():
            item = row_to_dict(t)
            item["status_text"] = status_text(t.status)
            cnt = await self.db.execute(
                select(func.count()).select_from(UserTenantModel).where(
                    UserTenantModel.tenant_id == t.id, not_deleted(UserTenantModel)
                )
            )
            item["user_count"] = int(cnt.scalar() or 0)
            rows.append(item)
        return page_result(rows, total, page, limit)

    async def get_detail(self, tenant_id: int) -> dict[str, Any] | None:
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        t = result.scalar_one_or_none()
        if not t:
            return None
        item = row_to_dict(t)
        cnt = await self.db.execute(
            select(func.count()).select_from(UserTenantModel).where(
                UserTenantModel.tenant_id == tenant_id, not_deleted(UserTenantModel)
            )
        )
        item["user_count"] = int(cnt.scalar() or 0)
        return item

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        obj = TenantModel(
            tenant_name=data.get("tenant_name"),
            tenant_code=data.get("tenant_code"),
            contact_name=data.get("contact_name"),
            contact_phone=data.get("contact_phone"),
            contact_email=data.get("contact_email"),
            address=data.get("address"),
            logo_url=data.get("logo_url"),
            status=int(data.get("status", 1)),
            expire_time=data.get("expire_time"),
            max_users=int(data.get("max_users") or 0),
            max_depts=int(data.get("max_depts") or 0),
            max_roles=int(data.get("max_roles") or 0),
            remark=data.get("remark"),
            created_by=operator,
            updated_by=operator,
        )
        self.db.add(obj)
        await self.db.flush()
        return row_to_dict(obj)

    async def update(self, tenant_id: int, data: dict[str, Any], operator: int) -> dict[str, Any]:
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="租户不存在", code=404)
        for field in (
            "tenant_name", "tenant_code", "contact_name", "contact_phone", "contact_email",
            "address", "logo_url", "status", "expire_time", "max_users", "max_depts", "max_roles", "remark",
        ):
            if field in data:
                setattr(obj, field, data[field])
        obj.updated_by = operator
        await self.db.flush()
        return row_to_dict(obj)

    async def delete(self, tenant_id: int) -> bool:
        if tenant_id == 1:
            raise CustomException(msg="默认租户不可删除", code=403)
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def update_status(self, tenant_id: int, status: int) -> bool:
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.status = status
        await self.db.flush()
        return True

    async def get_tenant_users(self, tenant_id: int, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = (
            select(UserTenantModel, UserModel)
            .join(UserModel, UserModel.id == UserTenantModel.user_id)
            .where(UserTenantModel.tenant_id == tenant_id, not_deleted(UserTenantModel), not_deleted(UserModel))
        )
        if params.get("username"):
            q = q.where(UserModel.username.like(f"%{params['username']}%"))
        if params.get("realname"):
            q = q.where(UserModel.realname.like(f"%{params['realname']}%"))
        if params.get("phone"):
            q = q.where(UserModel.phone.like(f"%{params['phone']}%"))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(q.order_by(UserTenantModel.id.desc()).offset((page - 1) * limit).limit(limit))
        rows = []
        for ut, u in result.all():
            rows.append(
                {
                    "id": ut.id,
                    "tenant_id": ut.tenant_id,
                    "user_id": u.id,
                    "username": u.username,
                    "realname": u.realname,
                    "phone": u.phone,
                    "email": u.email,
                    "is_default": ut.is_default,
                    "is_super": ut.is_super,
                    "status": u.status,
                    "join_time": ut.join_time.strftime("%Y-%m-%d %H:%M:%S") if ut.join_time else None,
                }
            )
        return page_result(rows, total, page, limit)

    async def get_available_users(self, tenant_id: int, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        in_tenant = select(UserTenantModel.user_id).where(
            UserTenantModel.tenant_id == tenant_id, not_deleted(UserTenantModel)
        )
        q = select(UserModel).where(not_deleted(UserModel), UserModel.id.notin_(in_tenant))
        if params.get("username"):
            q = q.where(UserModel.username.like(f"%{params['username']}%"))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(q.order_by(UserModel.id.desc()).offset((page - 1) * limit).limit(limit))
        rows = [row_to_dict(u, exclude={"password"}) for u in result.scalars().all()]
        return page_result(rows, total, page, limit)

    async def add_users(self, tenant_id: int, user_ids: list[int], operator: int) -> int:
        tq = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        tenant = tq.scalar_one_or_none()
        if not tenant:
            raise CustomException(msg="租户不存在", code=404)
        added = 0
        for uid in user_ids:
            exists = await self.db.execute(
                select(UserTenantModel).where(
                    UserTenantModel.user_id == uid, UserTenantModel.tenant_id == tenant_id, not_deleted(UserTenantModel)
                )
            )
            if exists.scalar_one_or_none():
                continue
            self.db.add(
                UserTenantModel(
                    user_id=uid,
                    tenant_id=tenant_id,
                    is_default=0,
                    join_time=datetime.now(),
                    created_by=operator,
                    updated_by=operator,
                )
            )
            added += 1
        await self.db.flush()
        return added

    async def remove_user(self, tenant_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(UserTenantModel).where(
                UserTenantModel.tenant_id == tenant_id, UserTenantModel.user_id == user_id, not_deleted(UserTenantModel)
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def set_admin(self, tenant_id: int, user_id: int, is_super: int) -> bool:
        result = await self.db.execute(
            select(UserTenantModel).where(
                UserTenantModel.tenant_id == tenant_id, UserTenantModel.user_id == user_id, not_deleted(UserTenantModel)
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.is_super = int(is_super)
        await self.db.flush()
        return True

    async def set_default(self, tenant_id: int, user_id: int, is_default: int) -> bool:
        if int(is_default) == 1:
            all_ut = await self.db.execute(
                select(UserTenantModel).where(UserTenantModel.user_id == user_id, not_deleted(UserTenantModel))
            )
            for ut in all_ut.scalars().all():
                ut.is_default = 1 if int(ut.tenant_id) == tenant_id else 0
        else:
            result = await self.db.execute(
                select(UserTenantModel).where(
                    UserTenantModel.tenant_id == tenant_id,
                    UserTenantModel.user_id == user_id,
                    not_deleted(UserTenantModel),
                )
            )
            obj = result.scalar_one_or_none()
            if obj:
                obj.is_default = 0
        await self.db.flush()
        return True
