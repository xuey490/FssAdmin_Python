from sqlalchemy import BigInteger, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin


class MenuModel(SaModelMixin):
    """全局菜单，无 tenant_id。"""

    __tablename__ = "sa_system_menu"
    __table_args__ = {"comment": "菜单权限表"}

    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    type: Mapped[int] = mapped_column(SmallInteger, default=1)
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    component: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=100)
    link_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_iframe: Mapped[int] = mapped_column(SmallInteger, default=2)
    is_keep_alive: Mapped[int] = mapped_column(SmallInteger, default=2)
    is_hidden: Mapped[int] = mapped_column(SmallInteger, default=2)
    is_fixed_tab: Mapped[int] = mapped_column(SmallInteger, default=2)
    is_full_page: Mapped[int] = mapped_column(SmallInteger, default=2)
    generate_id: Mapped[int] = mapped_column(Integer, default=0)
    generate_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
