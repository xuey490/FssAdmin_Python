"""日志表映射 sa_system_login_log / sa_system_oper_log。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin


class LoginLogModel(SaModelMixin):
    __tablename__ = "sa_system_login_log"
    __table_args__ = {"comment": "系统访问记录"}

    username: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ip_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os: Mapped[str | None] = mapped_column(String(50), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    message: Mapped[str | None] = mapped_column(String(50), nullable=True)
    login_time: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OperLogModel(SaModelMixin):
    __tablename__ = "sa_system_oper_log"
    __table_args__ = {"comment": "操作日志记录"}

    username: Mapped[str | None] = mapped_column(String(20), nullable=True)
    app: Mapped[str | None] = mapped_column(String(50), nullable=True)
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    router: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ip_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
