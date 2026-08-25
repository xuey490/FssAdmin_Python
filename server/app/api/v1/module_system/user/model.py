from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase, SaModelMixin, TenantMixin


class UserModel(SaModelMixin):
    """sa_system_user — 全局账号，无 tenant_id。"""

    __tablename__ = "sa_system_user"
    __table_args__ = {"comment": "用户表"}

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    realname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    signed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dashboard: Mapped[str | None] = mapped_column(String(255), default="work")
    dept_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_super: Mapped[int] = mapped_column(SmallInteger, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def is_superuser(self) -> bool:
        return bool(self.is_super)

    @property
    def name(self) -> str:
        return self.realname or self.username


class UserTenantModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_system_user_tenant"
    __table_args__ = {"comment": "用户租户关联"}

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    is_default: Mapped[int] = mapped_column(SmallInteger, default=0)
    join_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_super: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class UserRoleModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_system_user_role"
    __table_args__ = {"comment": "用户角色关联"}

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class UserDeptModel(TenantMixin):
    """无 delete_time（硬删表）。"""

    __tablename__ = "sa_system_user_dept"
    __table_args__ = {"comment": "用户部门关联"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserMenuModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_system_user_menu"
    __table_args__ = {"comment": "用户菜单关联"}

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    menu_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)


class UserPostModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_system_user_post"
    __table_args__ = {"comment": "用户岗位关联"}

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    post_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


UserRolesModel = UserRoleModel
