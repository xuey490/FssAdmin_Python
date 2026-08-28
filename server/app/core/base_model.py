from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.common.enums import PermissionFilterStrategy
from app.core.timezone import now


class MappedBase(AsyncAttrs, DeclarativeBase):
    """声明式基类。"""

    __abstract__: bool = True
    __permission_strategy__: PermissionFilterStrategy = PermissionFilterStrategy.DATA_SCOPE


class SaModelMixin(MappedBase):
    """对齐 sa_system_*：id + create_time/update_time/delete_time（软删）。"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, default=now, nullable=True)
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime, default=now, onupdate=now, nullable=True
    )
    delete_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True)


# 兼容旧 import 名（部分插件/工具可能仍引用）
ModelMixin = SaModelMixin


class TenantMixin(MappedBase):
    """行级租户字段（无 FK，避免强绑定 platform_tenant）。"""

    __abstract__ = True

    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="租户ID")
