from sqlalchemy import BigInteger, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase, SaModelMixin, TenantMixin


class RoleModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_system_role"
    __table_args__ = {"comment": "角色表"}

    parent_id: Mapped[int] = mapped_column(BigInteger, default=0)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    data_scope: Mapped[int] = mapped_column(SmallInteger, default=1)
    sort: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RoleMenuModel(MappedBase):
    """仅 id/role_id/menu_id（表无租户/软删字段）。"""

    __tablename__ = "sa_system_role_menu"
    __table_args__ = {"comment": "角色菜单关联"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    menu_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


class RoleDeptModel(MappedBase):
    """仅 id/role_id/dept_id。"""

    __tablename__ = "sa_system_role_dept"
    __table_args__ = {"comment": "角色部门关联"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
