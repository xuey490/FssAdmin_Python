from dataclasses import dataclass

from fastapi import Query
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.api.v1.module_system.dept.schema import DeptOutSchema
from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema, TenantBySchema, UserBySchema
from app.core.validator import role_permission_request_validator, validate_required_code


class RoleCreateSchema(BaseModel):
    """角色创建（对齐 sa_system_role；兼容 order/description）。"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=64, description="角色名称")
    code: str = Field(..., min_length=2, max_length=64, description="角色编码")
    sort: int | None = Field(
        default=100, ge=0, description="显示排序",
        validation_alias=AliasChoices("sort", "order"),
    )
    parent_id: int = Field(default=0, ge=0, description="父角色ID")
    level: int = Field(default=1, ge=1, description="层级")
    data_scope: int | None = Field(default=1, ge=1, le=5, description="数据权限范围")
    status: int = Field(default=1, ge=0, le=1, description="状态(1:启用 0:停用)")
    remark: str | None = Field(
        default=None, max_length=255, description="描述",
        validation_alias=AliasChoices("remark", "description"),
    )
    dept_ids: list[int] | None = Field(default=None, description="自定义数据权限部门")

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str):
        return validate_required_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("角色名称不能为空")
        return v


class RoleUpdateSchema(BaseModel):
    """角色更新（部分字段）。"""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=64)
    code: str | None = Field(default=None, max_length=64)
    sort: int | None = Field(default=None, ge=0, validation_alias=AliasChoices("sort", "order"))
    parent_id: int | None = Field(default=None, ge=0)
    level: int | None = Field(default=None, ge=1)
    data_scope: int | None = Field(default=None, ge=1, le=5)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(
        default=None, max_length=255,
        validation_alias=AliasChoices("remark", "description"),
    )
    dept_ids: list[int] | None = Field(default=None)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None):
        if value is None:
            return value
        v = value.strip()
        if not v:
            raise ValueError("角色名称不能为空")
        return v


class RolePermissionSettingSchema(BaseModel):
    data_scope: int = Field(default=1, ge=1, le=5, description="数据权限范围")
    role_ids: list[int] = Field(default_factory=list, description="角色ID列表")
    menu_ids: list[int] = Field(default_factory=list, description="菜单ID列表")
    dept_ids: list[int] = Field(default_factory=list, description="部门ID列表")

    @model_validator(mode="after")
    def validate_fields(self):
        return role_permission_request_validator(self)


class RoleMenusSchema(BaseModel):
    menu_ids: list[int] = Field(default_factory=list)


class MenuBriefSchema(BaseModel):
    id: int
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleOutSchema(BaseSchema, UserBySchema, TenantBySchema):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    code: str | None = None
    sort: int | None = None
    data_scope: int | None = None
    status: int | None = None
    remark: str | None = None
    menus: list[MenuBriefSchema] = Field(default_factory=list, description="角色菜单列表")
    depts: list[DeptOutSchema] = Field(default_factory=list, description="角色部门列表")


@dataclass
class RoleQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    name: str | None = Query(None, description="角色名称")
    code: str | None = Query(None, description="角色编码")
    status: int | None = Query(None, description="状态")

    def __post_init__(self) -> None:
        self.name = (QueueEnum.like.value, self.name)
        if self.code:
            self.code = (QueueEnum.like.value, self.code)
        if self.status is not None:
            self.status = (QueueEnum.eq.value, self.status)
