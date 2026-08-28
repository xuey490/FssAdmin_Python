from dataclasses import dataclass

from fastapi import Query
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema, TenantBySchema, UserBySchema
from app.core.validator import validate_required_code


class DeptCreateSchema(BaseModel):
    """部门创建（对齐 sa_system_dept；兼容 order/description）。"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=64, description="部门名称")
    code: str | None = Field(default=None, max_length=64, description="部门编码")
    sort: int = Field(
        default=0, ge=0, description="显示顺序",
        validation_alias=AliasChoices("sort", "order"),
    )
    leader_id: int | None = Field(default=None, ge=0, description="负责人用户ID")
    parent_id: int = Field(default=0, ge=0, description="父部门ID")
    status: int = Field(default=1, ge=0, le=1, description="状态(1:启用 0:停用)")
    remark: str | None = Field(
        default=None, max_length=255, description="备注",
        validation_alias=AliasChoices("remark", "description"),
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        v = (value or "").strip()
        if not v:
            raise ValueError("部门名称不能为空")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return None
        return validate_required_code(value)


class DeptUpdateSchema(BaseModel):
    """部门更新"""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=64)
    code: str | None = Field(default=None, max_length=64)
    sort: int | None = Field(default=None, ge=0, validation_alias=AliasChoices("sort", "order"))
    leader_id: int | None = Field(default=None, ge=0)
    parent_id: int | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(
        default=None, max_length=255,
        validation_alias=AliasChoices("remark", "description"),
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None):
        if value is None:
            return value
        v = value.strip()
        if not v:
            raise ValueError("部门名称不能为空")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)


class DeptOutSchema(BaseSchema, UserBySchema, TenantBySchema):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    code: str | None = None
    parent_id: int | None = None
    parent_name: str | None = Field(default=None, max_length=64, description="父部门名称")
    sort: int | None = None
    status: int | None = None
    remark: str | None = None
    leader_id: int | None = None


class DeptTreeOutSchema(DeptOutSchema):
    children: list["DeptTreeOutSchema"] | None = Field(default=None, description="子部门列表")


@dataclass
class DeptQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    name: str | None = Query(None, description="部门名称")
    status: int | None = Query(None, ge=0, le=1, description="状态")

    def __post_init__(self) -> None:
        self.name = (QueueEnum.like.value, self.name)
        if isinstance(self.status, int):
            self.status = (QueueEnum.eq.value, self.status)
