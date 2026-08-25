"""邮件日志表 sa_system_mail。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin


class MailLogModel(SaModelMixin):
    __tablename__ = "sa_system_mail"
    __table_args__ = {"comment": "邮件记录"}

    gateway: Mapped[str | None] = mapped_column(String(50), nullable=True)
    from_: Mapped[str | None] = mapped_column("from", String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(50), nullable=True)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    response: Mapped[str | None] = mapped_column(String(500), nullable=True)
