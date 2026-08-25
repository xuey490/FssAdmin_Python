"""附件表 sa_system_attachment / sa_system_category。"""

from sqlalchemy import BigInteger, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin


class AttachmentModel(SaModelMixin):
    __tablename__ = "sa_system_attachment"
    __table_args__ = {"comment": "附件信息表"}

    category_id: Mapped[int | None] = mapped_column(Integer, default=0, index=True)
    storage_mode: Mapped[int] = mapped_column(SmallInteger, default=1)
    origin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suffix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    size_byte: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    size_info: Mapped[str | None] = mapped_column(String(50), nullable=True)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AttachmentCategoryModel(SaModelMixin):
    __tablename__ = "sa_system_category"
    __table_args__ = {"comment": "附件分类表"}

    parent_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_name: Mapped[str] = mapped_column(String(100), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
