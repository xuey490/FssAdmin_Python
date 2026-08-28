from sqlalchemy import Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin, TenantMixin


class ArticleModel(SaModelMixin, TenantMixin):
    __tablename__ = "sa_article"
    __table_args__ = {"comment": "文章表"}

    category_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dept_id: Mapped[int | None] = mapped_column(Integer, default=0)
    image: Mapped[str | None] = mapped_column(String(1000), default="")
    describe: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    is_link: Mapped[int] = mapped_column(SmallInteger, default=2)
    link_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_hot: Mapped[int] = mapped_column(SmallInteger, default=2)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
