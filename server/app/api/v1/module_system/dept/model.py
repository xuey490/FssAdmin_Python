from sqlalchemy import BigInteger, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin, TenantMixin


class DeptModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_system_dept"
    __table_args__ = {"comment": "部门表"}

    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[str | None] = mapped_column(String(500), nullable=True)
    leader_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
