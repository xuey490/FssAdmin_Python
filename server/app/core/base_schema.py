from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.validator import DateTimeStr


class CommonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="编号ID")
    name: str = Field(description="名称")


class UserBySchema(BaseModel):
    """审计人字段（有列才有值）。"""

    model_config = ConfigDict(from_attributes=True)
    created_by: int | None = None
    updated_by: int | None = None


class TenantBySchema(BaseModel):
    """租户字段。"""

    model_config = ConfigDict(from_attributes=True)
    tenant_id: int | None = None


class AuthSchema(BaseModel):
    """权限认证上下文。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: Any = Field(default=None, description="UserModel", exclude=True)
    check_data_scope: bool = Field(default=True)
    db: AsyncSession | None = Field(default=None, exclude=True)
    tenant_id: int | None = Field(default=None)


class JWTPayloadSchema(BaseModel):
    """对齐 phpserver JWT claims：uid / name / tenant_id / roles。"""

    sub: str = Field(..., description="用户ID字符串")
    uid: int = Field(..., description="用户ID")
    name: str = Field(default="", description="用户名")
    nickname: str = Field(default="", description="昵称")
    tenant_id: int = Field(default=0, description="租户ID")
    role: Any = Field(default="user")
    roles: list[str] = Field(default_factory=list)
    is_refresh: bool = Field(default=False)
    exp: datetime | int = Field(...)
    token_version: str = Field(default="1", description="令牌版本（踢人/登出）")
    jti: str | None = Field(default=None, description="会话 ID")

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.sub:
            raise ValueError("sub 不能为空")
        return self


class JWTOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenPayloadSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    refresh_token: str = Field(
        ..., min_length=1,
        validation_alias=AliasChoices("refresh_token", "refreshToken"),
    )


class LogoutPayloadSchema(BaseModel):
    token: str = Field(default="")


class PageResultSchema[T](BaseModel):
    model_config = ConfigDict(from_attributes=True)
    page_no: int | None = None
    page_size: int | None = None
    total: int = 0
    has_next: bool | None = False
    items: list[T] = Field(default_factory=list)


class BatchDelete(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ids: list[int] = Field(..., min_length=1, validation_alias=AliasChoices("ids", "id"))

    @field_validator("ids", mode="before")
    @classmethod
    def split_ids(cls, value):
        if isinstance(value, str):
            return [int(x) for x in value.split(",") if x.strip()]
        if isinstance(value, int):
            return [value]
        return value


class IdsSchema(BaseModel):
    """批量 id 列表（允许空；兼容逗号分隔字符串）。"""

    ids: list[int] = Field(default_factory=list)

    @field_validator("ids", mode="before")
    @classmethod
    def split_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [int(x) for x in value.split(",") if x.strip()]
        if isinstance(value, int):
            return [value]
        return value


class StatusSchema(BaseModel):
    """状态开关。1=启用 0=停用；兼容 enabled。"""

    model_config = ConfigDict(populate_by_name=True)
    status: int = Field(default=1, ge=0, le=1, validation_alias=AliasChoices("status", "enabled"))


class BatchSetAvailable(BaseModel):
    ids: list[int] = Field(default_factory=list)
    status: int = Field(default=0, ge=0, le=1)


class UploadResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    file_path: str | None = None
    file_name: str | None = None
    origin_name: str | None = None
    file_url: str | None = None


class DownloadFileSchema(BaseModel):
    file_path: str
    file_name: str


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int | None = None
    created_time: DateTimeStr | None = Field(
        default=None,
        validation_alias=AliasChoices("created_time", "create_time"),
        serialization_alias="created_time",
    )
    updated_time: DateTimeStr | None = Field(
        default=None,
        validation_alias=AliasChoices("updated_time", "update_time"),
        serialization_alias="updated_time",
    )


def make_token_exp(seconds: int) -> datetime:
    return datetime.now() + timedelta(seconds=seconds)
