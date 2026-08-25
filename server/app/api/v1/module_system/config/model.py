"""配置表映射 sa_system_config / sa_system_config_group。"""

from sqlalchemy import Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SaModelMixin


class ConfigGroupModel(SaModelMixin):
    __tablename__ = "sa_system_config_group"
    __table_args__ = {"comment": "配置分组表"}

    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ConfigModel(SaModelMixin):
    __tablename__ = "sa_system_config"
    __table_args__ = {"comment": "参数配置信息表"}

    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    config_select_data: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
