"""认证服务：登录 / 切租户 / 用户信息（对齐 phpserver AuthController）。"""

from __future__ import annotations

import calendar
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, row_to_dict
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.menu.service import MenuService
from app.api.v1.module_system.role.model import RoleModel
from app.api.v1.module_system.tenant.model import TenantModel
from app.api.v1.module_system.user.model import UserModel, UserRoleModel, UserTenantModel
from app.common.enums import RedisInitKeyConfig
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.core.token_manager import TokenIssueContext, build_token_manager
from app.utils.captcha_util import CaptchaUtil
from app.utils.hash_bcrpy_util import PwdUtil

REFRESH_PREFIX = "refresh:token:"
CAPTCHA_PREFIX = f"{RedisInitKeyConfig.CAPTCHA_CODES.key}:"


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis | None = None) -> None:
        self.db = db
        self.redis = redis

    def _token_manager(self):
        return build_token_manager(self.redis)

    @staticmethod
    def _parse_ua(user_agent: str) -> tuple[str, str]:
        ua = (user_agent or "").lower()
        if "windows" in ua:
            os_name = "Windows"
        elif "android" in ua:
            os_name = "Android"
        elif "iphone" in ua or "ipad" in ua:
            os_name = "iOS"
        elif "mac os" in ua or "macintosh" in ua:
            os_name = "Mac OS"
        elif "linux" in ua:
            os_name = "Linux"
        else:
            os_name = "Unknown"
        if "edg/" in ua or "edg " in ua:
            browser = "Edge"
        elif "chrome" in ua and "chromium" not in ua:
            browser = "Chrome"
        elif "firefox" in ua:
            browser = "Firefox"
        elif "safari" in ua:
            browser = "Safari"
        else:
            browser = "Unknown"
        return os_name, browser

    async def _dept_name(self, user_id: int, tenant_id: int) -> str:
        from app.api.v1.module_system.user.model import UserDeptModel

        q = await self.db.execute(
            select(UserDeptModel.dept_id).where(
                UserDeptModel.user_id == user_id,
                UserDeptModel.tenant_id == tenant_id,
            )
        )
        dept_id = q.scalar_one_or_none()
        if not dept_id:
            uq = await self.db.execute(select(UserModel.dept_id).where(UserModel.id == user_id))
            dept_id = uq.scalar_one_or_none()
        if not dept_id:
            return ""
        dq = await self.db.execute(
            select(DeptModel.name).where(DeptModel.id == int(dept_id), not_deleted(DeptModel))
        )
        name = dq.scalar_one_or_none()
        return str(name or "")

    async def _issue_tokens(
        self,
        user: UserModel,
        tenant_id: int,
        *,
        remember: bool = False,
        client_ip: str = "",
        user_agent: str = "",
    ) -> dict[str, Any]:
        ttl = 604800 if remember else int(getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", 3600) or 3600)
        if ttl < 60:
            ttl = 3600

        role_codes = await self._role_codes(user.id, tenant_id, user)
        os_name, browser = self._parse_ua(user_agent)
        login_location = ""
        try:
            from app.utils.ip_local_util import IpLocalUtil

            login_location = (
                await IpLocalUtil.resolve_location_for_log(self.redis, client_ip or None) or ""
            )
        except Exception:
            login_location = ""

        pair = await self._token_manager().generate_token(
            TokenIssueContext(
                uid=int(user.id),
                username=user.username,
                nickname=user.realname or user.username,
                tenant_id=int(tenant_id),
                roles=role_codes,
                is_super=bool(int(user.is_super or 0) == 1),
                access_ttl=ttl,
                ipaddr=client_ip or None,
                dept_name=await self._dept_name(int(user.id), int(tenant_id)),
                login_location=login_location,
                os=os_name,
                browser=browser,
            )
        )
        return {
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "token_type": "Bearer",
            "expires_in": pair.expires_in,
            "tenant_id": tenant_id,
        }

    async def _role_codes(self, user_id: int, tenant_id: int, user: UserModel) -> list[str]:
        if int(user.is_super or 0) == 1:
            return ["super_admin", "admin"]
        q = await self.db.execute(
            select(RoleModel.code)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.tenant_id == tenant_id,
                not_deleted(UserRoleModel),
                not_deleted(RoleModel),
            )
        )
        codes = [c for c in q.scalars().all() if c]
        return codes or ["user"]

    async def tenants_by_username(self, username: str) -> list[dict[str, Any]]:
        if not username:
            return []
        uq = await self.db.execute(select(UserModel).where(UserModel.username == username, not_deleted(UserModel)))
        user = uq.scalar_one_or_none()
        if not user:
            return []
        return await self._user_tenants(user.id, only_valid=True)

    async def _user_tenants(self, user_id: int, only_valid: bool = False) -> list[dict[str, Any]]:
        q = await self.db.execute(
            select(UserTenantModel, TenantModel)
            .join(TenantModel, TenantModel.id == UserTenantModel.tenant_id)
            .where(UserTenantModel.user_id == user_id, not_deleted(UserTenantModel), not_deleted(TenantModel))
        )
        out = []
        for ut, t in q.all():
            if only_valid and not t.is_valid():
                continue
            out.append(
                {
                    "id": t.id,
                    "name": t.tenant_name,
                    "code": t.tenant_code,
                    "is_default": bool(ut.is_default),
                    "status": t.status,
                }
            )
        return out

    async def _verify_captcha(self, uuid: str, code: str) -> None:
        if not settings.CAPTCHA_ENABLE:
            return
        uuid = (uuid or "").strip()
        code = (code or "").strip()
        if not uuid or not code:
            raise CustomException(msg="验证码不能为空", code=400)
        if self.redis is None:
            raise CustomException(msg="验证码服务不可用", code=500)
        key = f"{CAPTCHA_PREFIX}{uuid}"
        stored = await self.redis.get(key)
        if stored is not None:
            await self.redis.delete(key)
        if not stored or str(stored).lower() != code.lower():
            raise CustomException(msg="验证码错误或已过期", code=400)

    async def login(self, data: dict[str, Any], client_ip: str = "", user_agent: str = "") -> dict[str, Any]:
        from app.api.v1.module_system.logs.service import LogService

        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        tenant_id = int(data.get("tenant_id") or 0)
        if not username or not password:
            raise CustomException(msg="用户名和密码不能为空", code=400)
        if not tenant_id:
            raise CustomException(msg="租户ID不能为空", code=400)
        await self._verify_captcha(str(data.get("uuid") or ""), str(data.get("code") or ""))

        uq = await self.db.execute(select(UserModel).where(UserModel.username == username, not_deleted(UserModel)))
        user = uq.scalar_one_or_none()
        if not user or not PwdUtil.verify_password(password, user.password):
            try:
                await LogService.write_login(
                    self.db, username=username, ip=client_ip, status=2, message="用户名或密码错误"
                )
            except Exception:
                pass
            raise CustomException(msg="用户名或密码错误", code=400)
        if int(user.status or 0) != 1:
            try:
                await LogService.write_login(
                    self.db, username=username, ip=client_ip, status=2, message="账号已被禁用"
                )
            except Exception:
                pass
            raise CustomException(msg="账号已被禁用", code=403)

        if int(user.is_super or 0) != 1:
            memb = await self.db.execute(
                select(UserTenantModel).where(
                    UserTenantModel.user_id == user.id,
                    UserTenantModel.tenant_id == tenant_id,
                    not_deleted(UserTenantModel),
                )
            )
            if not memb.scalar_one_or_none():
                try:
                    await LogService.write_login(
                        self.db, username=username, ip=client_ip, status=2, message="您不属于该租户"
                    )
                except Exception:
                    pass
                raise CustomException(msg="您不属于该租户", code=403)

        tq = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        tenant = tq.scalar_one_or_none()
        if not tenant or not tenant.is_valid():
            try:
                await LogService.write_login(
                    self.db, username=username, ip=client_ip, status=2, message="租户无效或已过期"
                )
            except Exception:
                pass
            raise CustomException(msg="租户无效或已过期", code=403)

        user.login_time = datetime.now()
        user.login_ip = client_ip or user.login_ip
        await self.db.flush()

        try:
            await LogService.write_login(
                self.db, username=username, ip=client_ip, status=1, message="登录成功"
            )
        except Exception:
            pass

        tokens = await self._issue_tokens(
            user,
            tenant_id,
            remember=bool(data.get("rememberPassword")),
            client_ip=client_ip,
            user_agent=user_agent,
        )
        auth = AuthSchema(db=self.db, tenant_id=tenant_id)
        auth.user = user
        menu_svc = MenuService(auth)
        menus = await menu_svc.get_user_menu_tree(user.id)
        permissions = await menu_svc.get_user_permissions(user.id)

        return {
            **tokens,
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.realname or user.username,
                "avatar": user.avatar or "",
                "is_admin": bool(user.is_super),
            },
            "menus": menus,
            "permissions": permissions if permissions != ["*"] else ["*"],
        }

    async def switch_tenant(self, auth: AuthSchema, tenant_id: int) -> dict[str, Any]:
        user: UserModel = auth.user
        if int(user.is_super or 0) != 1:
            memb = await self.db.execute(
                select(UserTenantModel).where(
                    UserTenantModel.user_id == user.id,
                    UserTenantModel.tenant_id == tenant_id,
                    not_deleted(UserTenantModel),
                )
            )
            if not memb.scalar_one_or_none():
                raise CustomException(msg="您不属于该租户", code=403)

        tq = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id, not_deleted(TenantModel)))
        tenant = tq.scalar_one_or_none()
        if not tenant or not tenant.is_valid():
            raise CustomException(msg="租户无效或已过期", code=403)

        # 设为默认
        all_ut = await self.db.execute(
            select(UserTenantModel).where(UserTenantModel.user_id == user.id, not_deleted(UserTenantModel))
        )
        for ut in all_ut.scalars().all():
            ut.is_default = 1 if int(ut.tenant_id) == tenant_id else 0
        await self.db.flush()

        tokens = await self._issue_tokens(user, tenant_id)
        auth.tenant_id = tenant_id
        from app.core.request_context import set_current_tenant

        set_current_tenant(tenant_id)
        menu_svc = MenuService(auth)
        return {
            **tokens,
            "tenant_id": tenant_id,
            "tenant_name": tenant.tenant_name,
            "menus": await menu_svc.get_user_menu_tree(user.id),
            "permissions": await menu_svc.get_user_permissions(user.id),
        }

    async def current_user_info(self, auth: AuthSchema) -> dict[str, Any]:
        user: UserModel = auth.user
        tid = int(auth.tenant_id or 0)
        menu_svc = MenuService(auth)
        permissions = await menu_svc.get_user_permissions(user.id)
        roles = await self._role_codes(user.id, tid, user)

        dept = None
        if user.dept_id:
            dq = await self.db.execute(
                select(DeptModel).where(DeptModel.id == user.dept_id, not_deleted(DeptModel))
            )
            d = dq.scalar_one_or_none()
            if d:
                dept = {"id": d.id, "name": d.name}

        tenant_info = None
        if tid:
            tq = await self.db.execute(select(TenantModel).where(TenantModel.id == tid, not_deleted(TenantModel)))
            t = tq.scalar_one_or_none()
            if t:
                tenant_info = {"id": t.id, "name": t.tenant_name, "code": t.tenant_code}

        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.realname or user.username,
            "realname": user.realname or "",
            "email": user.email or "",
            "phone": user.phone or "",
            "avatar": user.avatar or "",
            "gender": user.gender or "",
            "signed": user.signed or "",
            "remark": user.remark or "",
            "dashboard": user.dashboard or "work",
            "login_time": user.login_time.strftime("%Y-%m-%d %H:%M:%S") if user.login_time else None,
            "login_ip": user.login_ip or "",
            "is_admin": bool(user.is_super),
            "buttons": ["*"] if int(user.is_super or 0) == 1 else permissions,
            "roles": roles,
            "department": dept,
            "posts": [],
            "tenant": tenant_info,
        }

    async def captcha(self) -> dict[str, Any]:
        """生成图片验证码，对齐 web CaptchaResponse: result/uuid/image。"""
        uuid = secrets.token_hex(16)
        if not settings.CAPTCHA_ENABLE:
            # 关闭时返回透明占位图，登录侧跳过校验
            return {
                "result": 0,
                "uuid": uuid,
                "image": "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
            }
        if self.redis is None:
            raise CustomException(msg="验证码服务不可用", code=500)
        img_b64, code = CaptchaUtil.generate_captcha()
        await self.redis.setex(
            f"{CAPTCHA_PREFIX}{uuid}",
            int(settings.CAPTCHA_EXPIRE_SECONDS),
            str(code).lower(),
        )
        return {
            "result": 1,
            "uuid": uuid,
            "image": f"data:image/png;base64,{img_b64}",
        }

    async def logout(self, access_token: str | None = None, *, kick_all: bool = False) -> None:
        tm = self._token_manager()
        if kick_all and access_token:
            claims = await tm.parse_token(access_token)
            if claims:
                await tm.invalidate_user_sessions(int(claims.uid))
                return
        if access_token:
            await tm.invalidate_token(access_token)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        if not refresh_token:
            raise CustomException(msg="刷新令牌无效", code=401, status_code=401)

        tm = self._token_manager()
        uid = await tm.resolve_refresh(refresh_token)

        # ponytail: 兼容升级前 opaque refresh:token:{sha256} 键，读完即删
        if uid is None and self.redis is not None:
            h = hashlib.sha256(refresh_token.encode()).hexdigest()
            legacy = await self.redis.get(f"{REFRESH_PREFIX}{h}")
            if legacy:
                await self.redis.delete(f"{REFRESH_PREFIX}{h}")
                try:
                    uid = int(legacy.decode() if isinstance(legacy, bytes) else legacy)
                except (TypeError, ValueError):
                    uid = None

        if not uid:
            raise CustomException(msg="刷新令牌已过期", code=401, status_code=401)

        uq = await self.db.execute(select(UserModel).where(UserModel.id == int(uid), not_deleted(UserModel)))
        user = uq.scalar_one_or_none()
        if not user:
            raise CustomException(msg="用户不存在", code=401, status_code=401)
        ut = await self.db.execute(
            select(UserTenantModel)
            .where(UserTenantModel.user_id == user.id, not_deleted(UserTenantModel))
            .order_by(UserTenantModel.is_default.desc())
        )
        row = ut.scalars().first()
        tenant_id = int(row.tenant_id) if row else 1
        return await self._issue_tokens(user, tenant_id)

    async def statistics(self) -> dict[str, int]:
        """对齐 phpserver SystemController::statistics。"""
        from app.api.v1.module_system.attachment.model import AttachmentModel
        from app.api.v1.module_system.logs.model import LoginLogModel, OperLogModel

        user = int(
            (await self.db.execute(select(func.count()).select_from(UserModel).where(not_deleted(UserModel)))).scalar()
            or 0
        )
        attach = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(AttachmentModel).where(not_deleted(AttachmentModel))
                )
            ).scalar()
            or 0
        )
        login = int(
            (
                await self.db.execute(select(func.count()).select_from(LoginLogModel).where(not_deleted(LoginLogModel)))
            ).scalar()
            or 0
        )
        operate = int(
            (
                await self.db.execute(select(func.count()).select_from(OperLogModel).where(not_deleted(OperLogModel)))
            ).scalar()
            or 0
        )
        return {"user": user, "attach": attach, "login": login, "operate": operate}

    async def login_chart(self) -> dict[str, list[Any]]:
        """近 30 天每日登录折线图。"""
        from app.api.v1.module_system.logs.model import LoginLogModel

        login_date: list[str] = []
        login_count: list[int] = []
        today = datetime.now().date()
        for offset in range(29, -1, -1):
            day = today - timedelta(days=offset)
            start = datetime.combine(day, datetime.min.time())
            end = datetime.combine(day, datetime.max.time())
            count = int(
                (
                    await self.db.execute(
                        select(func.count())
                        .select_from(LoginLogModel)
                        .where(
                            not_deleted(LoginLogModel),
                            LoginLogModel.login_time >= start,
                            LoginLogModel.login_time <= end,
                        )
                    )
                ).scalar()
                or 0
            )
            login_date.append(day.isoformat())
            login_count.append(count)
        return {"login_date": login_date, "login_count": login_count}

    async def login_bar_chart(self) -> dict[str, list[Any]]:
        """近 12 个月登录柱状图。"""
        from app.api.v1.module_system.logs.model import LoginLogModel

        login_month: list[str] = []
        login_count: list[int] = []
        now = datetime.now()
        # 以当月 1 号为锚点，往前推 11 个月
        anchor = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        months: list[datetime] = []
        cur = anchor
        for _ in range(12):
            months.append(cur)
            # 上一个月
            prev_year = cur.year if cur.month > 1 else cur.year - 1
            prev_month = cur.month - 1 if cur.month > 1 else 12
            cur = cur.replace(year=prev_year, month=prev_month)
        months.reverse()

        for month_start in months:
            last_day = calendar.monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day, hour=23, minute=59, second=59)
            count = int(
                (
                    await self.db.execute(
                        select(func.count())
                        .select_from(LoginLogModel)
                        .where(
                            not_deleted(LoginLogModel),
                            LoginLogModel.login_time >= month_start,
                            LoginLogModel.login_time <= month_end,
                        )
                    )
                ).scalar()
                or 0
            )
            login_month.append(month_start.strftime("%Y-%m"))
            login_count.append(count)
        return {"login_month": login_month, "login_count": login_count}
