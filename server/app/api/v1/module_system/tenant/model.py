from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin


class TenantModel(SaModelMixin):
    __tablename__ = "sa_system_tenant"
    __table_args__ = {"comment": "租户信息表"}

    tenant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    max_users: Mapped[int] = mapped_column(Integer, default=0)
    max_depts: Mapped[int] = mapped_column(Integer, default=0)
    max_roles: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_by: Mapped[int] = mapped_column(BigInteger, default=0)

    @property
    def name(self) -> str:
        return self.tenant_name

    @property
    def code(self) -> str:
        return self.tenant_code

    def is_valid(self) -> bool:
        if self.delete_time is not None:
            return False
        if int(self.status or 0) != 1:
            return False
        if self.expire_time and self.expire_time < datetime.now():
            return False
        return True
