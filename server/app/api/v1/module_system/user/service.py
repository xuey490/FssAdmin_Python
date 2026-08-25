"""用户服务（对齐 phpserver SysUserService）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict, status_text
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.menu.service import MenuService
from app.api.v1.module_system.post.model import PostModel
from app.api.v1.module_system.role.model import RoleModel
from app.api.v1.module_system.user.model import (
    UserDeptModel,
    UserMenuModel,
    UserModel,
    UserPostModel,
    UserRoleModel,
    UserTenantModel,
)
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.utils.hash_bcrpy_util import PwdUtil


class UserService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db: AsyncSession = auth.db  # type: ignore[assignment]

    @property
    def tenant_id(self) -> int:
        return int(self.auth.tenant_id or 0)

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        tid = self.tenant_id
        tenant_uids = select(UserTenantModel.user_id).where(
            UserTenantModel.tenant_id == tid, not_deleted(UserTenantModel)
        )
        q = select(UserModel).where(not_deleted(UserModel), UserModel.id.in_(tenant_uids))
        if params.get("username"):
            q = q.where(UserModel.username.like(f"%{params['username']}%"))
        if params.get("phone"):
            q = q.where(UserModel.phone.like(f"%{params['phone']}%"))
        if params.get("email"):
            q = q.where(UserModel.email.like(f"%{params['email']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(UserModel.status == int(params["status"]))
        if params.get("dept_id"):
            dept_uid = select(UserDeptModel.user_id).where(
                UserDeptModel.dept_id == int(params["dept_id"]),
                UserDeptModel.tenant_id == tid,
            )
            q = q.where(UserModel.id.in_(dept_uid))

        count_q = select(func.count()).select_from(q.subquery())
        total = int((await self.db.execute(count_q)).scalar() or 0)
        result = await self.db.execute(q.order_by(UserModel.id.desc()).offset((page - 1) * limit).limit(limit))
        users = list(result.scalars().all())
        user_ids = [u.id for u in users]

        # 批量加载当前租户下的用户部门（不用 user.dept_id 全局字段）
        dept_by_user: dict[int, DeptModel] = {}
        if user_ids and tid > 0:
            links = (
                await self.db.execute(
                    select(UserDeptModel).where(
                        UserDeptModel.user_id.in_(user_ids), UserDeptModel.tenant_id == tid
                    )
                )
            ).scalars().all()
            dept_ids = list({int(x.dept_id) for x in links if x.dept_id})
            depts: dict[int, DeptModel] = {}
            if dept_ids:
                for dept in (
                    await self.db.execute(
                        select(DeptModel).where(DeptModel.id.in_(dept_ids), not_deleted(DeptModel))
                    )
                ).scalars().all():
                    depts[int(dept.id)] = dept
            for link in links:
                dept = depts.get(int(link.dept_id))
                if dept is not None:
                    dept_by_user[int(link.user_id)] = dept

        rows = []
        for u in users:
            d = row_to_dict(u, exclude={"password"})
            d["status_text"] = status_text(u.status)
            dept = dept_by_user.get(u.id)
            if dept is not None:
                d["dept_id"] = dept.id
                d["dept"] = row_to_dict(dept)
            else:
                d["dept_id"] = None
                d["dept"] = None
            rows.append(d)
        return page_result(rows, total, page, limit)

    async def get_detail(self, user_id: int) -> dict[str, Any] | None:
        """对齐 phpserver SysUserService::getDetail（含 roleList/postList/dept/menu_ids）。"""
        tid = self.tenant_id
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        u = result.scalar_one_or_none()
        if not u:
            return None
        d = row_to_dict(u, exclude={"password"})

        rq = await self.db.execute(
            select(UserRoleModel.role_id).where(
                UserRoleModel.user_id == user_id, UserRoleModel.tenant_id == tid, not_deleted(UserRoleModel)
            )
        )
        role_ids = list(rq.scalars().all())
        d["role_ids"] = role_ids
        if role_ids:
            roles = await self.db.execute(
                select(RoleModel).where(RoleModel.id.in_(role_ids), RoleModel.status == 1, not_deleted(RoleModel))
            )
            d["roleList"] = [row_to_dict(r) for r in roles.scalars().all()]
        else:
            d["roleList"] = []

        pq = await self.db.execute(
            select(UserPostModel.post_id).where(
                UserPostModel.user_id == user_id,
                UserPostModel.tenant_id == tid,
                UserPostModel.status == 1,
                not_deleted(UserPostModel),
            )
        )
        post_ids = list(pq.scalars().all())
        d["post_ids"] = post_ids
        if post_ids:
            posts = await self.db.execute(
                select(PostModel).where(PostModel.id.in_(post_ids), PostModel.status == 1, not_deleted(PostModel))
            )
            d["postList"] = [row_to_dict(p) for p in posts.scalars().all()]
        else:
            d["postList"] = []

        ud = await self.db.execute(
            select(UserDeptModel.dept_id).where(UserDeptModel.user_id == user_id, UserDeptModel.tenant_id == tid)
        )
        dept_id = ud.scalar_one_or_none()
        if dept_id:
            d["dept_id"] = dept_id
            dq = await self.db.execute(select(DeptModel).where(DeptModel.id == dept_id, not_deleted(DeptModel)))
            dept = dq.scalar_one_or_none()
            d["dept"] = row_to_dict(dept) if dept else None
        else:
            d["dept_id"] = None
            d["dept"] = None

        d["menu_ids"] = await self.get_menus(user_id)
        return d

    async def _sync_roles(self, user_id: int, role_ids: list[int], operator: int) -> None:
        tid = self.tenant_id
        old = await self.db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id, UserRoleModel.tenant_id == tid, not_deleted(UserRoleModel)
            )
        )
        now = datetime.now()
        for row in old.scalars().all():
            row.delete_time = now
        for rid in role_ids or []:
            self.db.add(
                UserRoleModel(user_id=user_id, role_id=int(rid), tenant_id=tid, created_by=operator, updated_by=operator)
            )
        await self.db.flush()

    async def _sync_dept(self, user_id: int, dept_id: int | None, operator: int) -> None:
        # uk_user_tenant(user_id, tenant_id)：同 flush 里 delete+insert 会撞唯一键，改为 upsert
        tid = self.tenant_id
        old = (
            await self.db.execute(
                select(UserDeptModel).where(UserDeptModel.user_id == user_id, UserDeptModel.tenant_id == tid)
            )
        ).scalar_one_or_none()
        if not dept_id:
            if old is not None:
                await self.db.delete(old)
                await self.db.flush()
            return
        if old is not None:
            old.dept_id = int(dept_id)
            old.updated_by = operator
        else:
            self.db.add(
                UserDeptModel(
                    user_id=user_id, dept_id=int(dept_id), tenant_id=tid, created_by=operator, updated_by=operator
                )
            )
        await self.db.flush()

    async def _sync_posts(self, user_id: int, post_ids: list[int], operator: int) -> None:
        tid = self.tenant_id
        old = await self.db.execute(
            select(UserPostModel).where(
                UserPostModel.user_id == user_id, UserPostModel.tenant_id == tid, not_deleted(UserPostModel)
            )
        )
        now = datetime.now()
        for row in old.scalars().all():
            row.delete_time = now
        for pid in post_ids or []:
            self.db.add(
                UserPostModel(user_id=user_id, post_id=int(pid), tenant_id=tid, created_by=operator, updated_by=operator)
            )
        await self.db.flush()

    async def create(self, data: dict[str, Any], operator: int) -> dict[str, Any]:
        username = (data.get("username") or "").strip()
        if not username:
            raise CustomException(msg="用户名不能为空", code=400)
        exists = await self.db.execute(select(UserModel).where(UserModel.username == username, not_deleted(UserModel)))
        if exists.scalar_one_or_none():
            raise CustomException(msg="用户名已存在", code=400)
        password = data.get("password") or "123456"
        obj = UserModel(
            username=username,
            password=PwdUtil.hash_password(password),
            realname=data.get("realname"),
            email=data.get("email"),
            phone=data.get("phone"),
            avatar=data.get("avatar"),
            gender=data.get("gender"),
            dept_id=data.get("dept_id"),
            status=int(data.get("status", 1)),
            remark=data.get("remark"),
            dashboard=data.get("dashboard") or "work",
            created_by=operator,
            updated_by=operator,
        )
        self.db.add(obj)
        await self.db.flush()
        tid = self.tenant_id
        if tid > 0:
            self.db.add(
                UserTenantModel(
                    user_id=obj.id, tenant_id=tid, is_default=0, join_time=datetime.now(), created_by=operator, updated_by=operator
                )
            )
        await self._sync_roles(obj.id, data.get("role_ids") or [], operator)
        await self._sync_dept(obj.id, data.get("dept_id"), operator)
        await self._sync_posts(obj.id, data.get("post_ids") or [], operator)
        if data.get("menu_ids") is not None:
            await self.save_menus(obj.id, data.get("menu_ids") or [], operator)
        await self.db.flush()
        return row_to_dict(obj, exclude={"password"})

    async def update(self, user_id: int, data: dict[str, Any], operator: int) -> dict[str, Any]:
        if user_id == 1:
            raise CustomException(msg="系统管理员不可修改", code=403)
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="用户不存在", code=404)
        for field in ("realname", "email", "phone", "avatar", "gender", "remark", "dashboard", "status", "dept_id"):
            if field in data:
                setattr(obj, field, data[field])
        if data.get("password"):
            obj.password = PwdUtil.hash_password(data["password"])
        obj.updated_by = operator
        if "role_ids" in data:
            await self._sync_roles(user_id, data.get("role_ids") or [], operator)
        if "dept_id" in data:
            await self._sync_dept(user_id, data.get("dept_id"), operator)
        if "post_ids" in data:
            await self._sync_posts(user_id, data.get("post_ids") or [], operator)
        if "menu_ids" in data:
            await self.save_menus(user_id, data.get("menu_ids") or [], operator)
        await self.db.flush()
        return row_to_dict(obj, exclude={"password"})

    async def update_profile(self, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """个人中心改资料（含超管自己），仅允许安全字段。"""
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="用户不存在", code=404)
        for field in ("realname", "email", "phone", "avatar", "gender", "signed"):
            if field in data and data[field] is not None:
                setattr(obj, field, data[field])
        obj.updated_by = user_id
        await self.db.flush()
        return {
            "id": obj.id,
            "username": obj.username,
            "realname": obj.realname,
            "nickname": obj.realname or obj.username,
            "email": obj.email,
            "phone": obj.phone,
            "gender": obj.gender,
            "signed": obj.signed,
            "avatar": obj.avatar,
        }

    async def change_own_password(self, user_id: int, old_password: str, new_password: str) -> None:
        """个人中心改密码：校验旧密码。"""
        if not old_password or not new_password:
            raise CustomException(msg="旧密码和新密码不能为空", code=400)
        if len(new_password) < 6:
            raise CustomException(msg="新密码长度不能少于6位", code=400)
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            raise CustomException(msg="用户不存在", code=404)
        if not PwdUtil.verify_password(old_password, obj.password):
            raise CustomException(msg="旧密码错误", code=400)
        obj.password = PwdUtil.hash_password(new_password)
        obj.updated_by = user_id
        await self.db.flush()

    async def delete(self, user_id: int) -> bool:
        if user_id == 1:
            raise CustomException(msg="系统管理员不可删除", code=403)
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.delete_time = datetime.now()
        await self.db.flush()
        return True

    async def update_status(self, user_id: int, status: int) -> bool:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.status = status
        await self.db.flush()
        return True

    async def reset_password(self, user_id: int, password: str) -> bool:
        if len(password) < 6:
            raise CustomException(msg="密码长度至少6位", code=400)
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.password = PwdUtil.hash_password(password)
        await self.db.flush()
        return True

    async def change_password(self, user_id: int, data: dict[str, Any]) -> bool:
        password = data.get("password") or data.get("newPassword") or ""
        return await self.reset_password(user_id, password)

    async def set_home_page(self, user_id: int, dashboard: str) -> bool:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, not_deleted(UserModel)))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        obj.dashboard = dashboard
        await self.db.flush()
        return True

    async def get_menus(self, user_id: int) -> list[int]:
        tid = self.tenant_id
        q = await self.db.execute(
            select(UserMenuModel.menu_id).where(
                UserMenuModel.user_id == user_id, UserMenuModel.tenant_id == tid, not_deleted(UserMenuModel)
            )
        )
        return list(q.scalars().all())

    async def save_menus(self, user_id: int, menu_ids: list[int], operator: int) -> bool:
        """对齐 phpserver SysUserMenu::syncUserMenus：硬删当前租户下该用户关联后再写入。"""
        tid = self.tenant_id
        menu_svc = MenuService(self.auth)
        menu_ids = await menu_svc.expand_with_parent_ids([int(x) for x in menu_ids])
        # uk_user_menu(user_id,menu_id,tenant_id)：软删占唯一键，必须硬删
        await self.db.execute(
            delete(UserMenuModel).where(
                UserMenuModel.user_id == user_id,
                UserMenuModel.tenant_id == tid,
            )
        )
        for mid in menu_ids:
            self.db.add(
                UserMenuModel(user_id=user_id, menu_id=mid, tenant_id=tid, created_by=operator, updated_by=operator)
            )
        await self.db.flush()
        return True

    async def clear_cache(self, user_id: int) -> bool:
        return True

    async def get_selector_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """对齐 phpserver SysUserService::getSelectorList（sa-user 组件）。"""
        page = max(1, int(params.get("page") or 1))
        limit = max(1, int(params.get("limit") or 5))
        keyword = str(params.get("keyword") or "").strip()
        tid = self.tenant_id

        q = select(UserModel).where(not_deleted(UserModel))
        if tid > 0:
            tenant_uids = select(UserTenantModel.user_id).where(
                UserTenantModel.tenant_id == tid, not_deleted(UserTenantModel)
            )
            q = q.where(UserModel.id.in_(tenant_uids))
        if keyword:
            like = f"%{keyword}%"
            q = q.where(
                or_(
                    UserModel.username.like(like),
                    UserModel.realname.like(like),
                    UserModel.phone.like(like),
                )
            )
        if params.get("status") not in (None, ""):
            q = q.where(UserModel.status == int(params["status"]))

        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        result = await self.db.execute(q.order_by(UserModel.id.desc()).offset((page - 1) * limit).limit(limit))
        rows = [
            {
                "id": u.id,
                "username": u.username,
                "realname": u.realname,
                "phone": u.phone,
                "avatar": u.avatar,
                "email": u.email,
                "status": u.status,
            }
            for u in result.scalars().all()
        ]
        return {"list": rows, "total": total, "page": page, "limit": limit}
