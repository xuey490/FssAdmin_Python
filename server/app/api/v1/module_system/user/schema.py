from dataclasses import dataclass

from fastapi import Query
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.api.v1.module_system.role.schema import MenuBriefSchema, RoleOutSchema
from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema, CommonSchema, TenantBySchema, UserBySchema
from app.core.validator import (
    avatar_validator,
    email_validator,
    mobile_validator,
    password_validator,
    phone_validator,
    username_validator,
)


class CurrentUserUpdateSchema(BaseModel):
    """基础用户信息"""

    name: str | None = Field(default=None, max_length=32, description="名称")
    mobile: str | None = Field(default=None, max_length=11, description="手机号")
    email: EmailStr | None = Field(default=None, description="邮箱")
    gender: str | None = Field(default=None, max_length=1, description="性别(0:男 1:女 2:未知)")
    avatar: str | None = Field(default=None, max_length=255, description="头像")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None):
        """校验手机号格式"""
        return mobile_validator(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        """校验邮箱格式"""
        if not value:
            return value
        return email_validator(value)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str | None):
        """校验性别：仅支持 0(男)、1(女)、2(未知)"""
        if value and value not in {"0", "1", "2"}:
            raise ValueError("性别仅支持 0(男)、1(女)、2(未知)")
        return value

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: str | None):
        return avatar_validator(value)

    @model_validator(mode="after")
    def check_model(self):
        """校验基础用户信息长度约束"""
        if self.name and len(self.name) > 32:
            raise ValueError("名称长度不能超过 32 个字符")
        return self


class UserRegisterSchema(BaseModel):
    """注册"""

    name: str | None = Field(default=None, max_length=32, description="姓名")
    mobile: str | None = Field(default=None, max_length=11, description="手机号")
    username: str = Field(..., min_length=3, max_length=32, description="账号")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    role_ids: list[int] | None = Field(default=[1], description="角色ID列表")
    created_id: int | None = Field(default=1, description="创建人ID")
    description: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None):
        """校验手机号格式"""
        return mobile_validator(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        """校验账号：字母开头，3-32 位，仅含字母/数字/_ . -"""
        v = value.strip()
        if not v:
            raise ValueError("账号不能为空")
        import re

        if not re.match(r"^[A-Za-z][A-Za-z0-9_.-]{2,31}$", v):
            raise ValueError("账号需以字母开头，3-32 位，仅允许字母、数字、_ . -")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        """校验密码：6-128 位"""
        if len(value) < 6:
            raise ValueError("密码长度不能少于 6 位")
        if len(value) > 128:
            raise ValueError("密码长度不能超过 128 位")
        return value

    @model_validator(mode="after")
    def check_model(self):
        """校验注册信息长度约束"""
        if self.name and len(self.name) > 32:
            raise ValueError("姓名长度不能超过 32 个字符")
        if self.username and len(self.username) > 32:
            raise ValueError("账号长度不能超过 32 个字符")
        if self.description and len(self.description) > 255:
            raise ValueError("备注长度不能超过 255 个字符")
        return self


class UserForgetPasswordSchema(BaseModel):
    """忘记密码"""

    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")
    mobile: str | None = Field(default=None, max_length=11, description="手机号")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        """校验账号：字母开头，3-32 位"""
        v = value.strip()
        if not v:
            raise ValueError("账号不能为空")
        import re

        if not re.match(r"^[A-Za-z][A-Za-z0-9_.-]{2,31}$", v):
            raise ValueError("账号需以字母开头，3-32 位，仅允许字母、数字、_ . -")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str):
        """校验密码：6-128 位"""
        if len(value) < 6:
            raise ValueError("密码长度不能少于 6 位")
        if len(value) > 128:
            raise ValueError("密码长度不能超过 128 位")
        return value

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None):
        """校验手机号格式"""
        return mobile_validator(value)


class UserChangePasswordSchema(BaseModel):
    """修改密码"""

    model_config = ConfigDict(populate_by_name=True)

    old_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="旧密码",
        validation_alias=AliasChoices("old_password", "oldPassword"),
    )
    new_password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="新密码",
        validation_alias=AliasChoices("new_password", "newPassword"),
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str):
        return password_validator(value, required=True)


class ResetPasswordSchema(BaseModel):
    """重置密码"""

    id: int = Field(default=0, description="主键ID（已弃用，由路径参数传入）")
    password: str = Field(..., min_length=6, max_length=128, description="新密码")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        return password_validator(value, required=True)


class UserCreateSchema(BaseModel):
    """新增用户（字段对齐 sa_system_user；兼容 name/mobile/description/position_ids）。"""

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str | None = Field(default=None, max_length=128, description="密码")
    realname: str | None = Field(
        default=None, max_length=64, description="姓名",
        validation_alias=AliasChoices("realname", "name"),
    )
    phone: str | None = Field(
        default=None, max_length=20, description="手机号",
        validation_alias=AliasChoices("phone", "mobile"),
    )
    email: str | None = Field(default=None, max_length=128, description="邮箱")
    gender: str | None = Field(default=None, max_length=10, description="性别")
    avatar: str | None = Field(default=None, max_length=255, description="头像")
    status: int = Field(default=1, ge=0, le=1, description="状态(1:启用 0:停用)")
    remark: str | None = Field(
        default=None, max_length=255, description="备注",
        validation_alias=AliasChoices("remark", "description"),
    )
    dept_id: int | None = Field(default=None, description="部门ID")
    tenant_id: int | None = Field(default=None, description="租户ID")
    role_ids: list[int] = Field(default_factory=list, description="角色ID列表")
    post_ids: list[int] = Field(
        default_factory=list, description="岗位ID列表",
        validation_alias=AliasChoices("post_ids", "position_ids"),
    )
    menu_ids: list[int] | None = Field(default=None, description="菜单ID列表")
    dashboard: str | None = Field(default=None, max_length=255, description="首页")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        return username_validator(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None):
        return password_validator(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None):
        return phone_validator(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        if not value:
            return value
        return email_validator(value)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: str | None):
        return avatar_validator(value)


class UserUpdateSchema(BaseModel):
    """更新用户"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    username: str | None = Field(default=None, max_length=32, description="用户名")
    password: str | None = Field(default=None, max_length=128, description="密码")
    realname: str | None = Field(
        default=None, max_length=64, description="姓名",
        validation_alias=AliasChoices("realname", "name"),
    )
    phone: str | None = Field(
        default=None, max_length=20, description="手机号",
        validation_alias=AliasChoices("phone", "mobile"),
    )
    email: str | None = Field(default=None, max_length=128, description="邮箱")
    gender: str | None = Field(default=None, max_length=10, description="性别")
    avatar: str | None = Field(default=None, max_length=255, description="头像")
    status: int | None = Field(default=None, ge=0, le=1, description="状态")
    remark: str | None = Field(
        default=None, max_length=255, description="备注",
        validation_alias=AliasChoices("remark", "description"),
    )
    dept_id: int | None = Field(default=None, description="部门ID")
    role_ids: list[int] | None = Field(default=None, description="角色ID列表")
    post_ids: list[int] | None = Field(
        default=None, description="岗位ID列表",
        validation_alias=AliasChoices("post_ids", "position_ids"),
    )
    menu_ids: list[int] | None = Field(default=None, description="菜单ID列表")
    dashboard: str | None = Field(default=None, max_length=255, description="首页")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None):
        if not value:
            return value
        return username_validator(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None):
        return password_validator(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None):
        return phone_validator(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        if not value:
            return value
        return email_validator(value)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: str | None):
        return avatar_validator(value)


class ProfileUpdateSchema(BaseModel):
    """个人中心改资料"""

    model_config = ConfigDict(populate_by_name=True)

    realname: str | None = Field(
        default=None, max_length=64,
        validation_alias=AliasChoices("realname", "name"),
    )
    phone: str | None = Field(
        default=None, max_length=20,
        validation_alias=AliasChoices("phone", "mobile"),
    )
    email: str | None = Field(default=None, max_length=128)
    gender: str | None = Field(default=None, max_length=10)
    signed: str | None = Field(default=None, max_length=255)
    avatar: str | None = Field(default=None, max_length=255)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None):
        return phone_validator(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        if not value:
            return value
        return email_validator(value)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: str | None):
        return avatar_validator(value)


class UserMenusSchema(BaseModel):
    menu_ids: list[int] = Field(default_factory=list)


class DashboardSchema(BaseModel):
    dashboard: str = Field(default="work", max_length=255)


class UserOutSchema(BaseSchema, UserBySchema, TenantBySchema):
    """响应"""

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    username: str | None = Field(default=None, max_length=32, description="用户名")
    realname: str | None = Field(default=None, max_length=64, description="姓名")
    phone: str | None = Field(default=None, description="手机号")
    email: str | None = Field(default=None, description="邮箱")
    gender: str | None = Field(default=None, description="性别")
    avatar: str | None = Field(default=None, description="头像")
    status: int | None = Field(default=None, description="状态")
    remark: str | None = Field(default=None, description="备注")
    dept_id: int | None = Field(default=None, description="部门ID")
    tenant_id: int | None = Field(
        default=None,
        exclude=True,
        description="创建入参使用；列表/详情出参见 tenant",
    )
    gitee_login: str | None = Field(default=None, max_length=32, description="Gitee登录")
    github_login: str | None = Field(default=None, max_length=32, description="Github登录")
    wx_login: str | None = Field(default=None, max_length=32, description="微信登录")
    qq_login: str | None = Field(default=None, max_length=32, description="QQ登录")
    dept_name: str | None = Field(default=None, description="部门名称")
    dept: CommonSchema | None = Field(default=None, description="部门")
    positions: list[CommonSchema] | None = Field(default=[], description="岗位")
    roles: list[RoleOutSchema] | None = Field(default=[], description="角色")
    menus: list[MenuBriefSchema] | None = Field(default=[], description="菜单")


@dataclass
class UserQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    """
    用户管理查询参数（继承标准 Mixin）

    支持：
    - 时间范围（BaseQueryParam）
    - 创建人/更新人筛选（UserByQueryParam）
    - 租户筛选（TenantByQueryParam）
    - 业务字段：用户名、名称、手机号、邮箱、部门、状态
    """

    username: str | None = Query(None, description="用户名")
    name: str | None = Query(None, description="名称")
    mobile: str | None = Query(None, description="手机号", pattern=r"^1[3-9]\d{9}$")
    email: str | None = Query(
        None,
        description="邮箱",
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    )
    dept_id: int | None = Query(None, description="部门ID")
    status: int | None = Query(None, description="是否可用")

    def __post_init__(self) -> None:
        self.username = (QueueEnum.like.value, self.username)
        self.name = (QueueEnum.like.value, self.name)
        if self.mobile:
            self.mobile = (QueueEnum.like.value, self.mobile)
        if self.email:
            self.email = (QueueEnum.like.value, self.email)
        if self.dept_id:
            self.dept_id = (QueueEnum.eq.value, self.dept_id)
        if self.status:
            self.status = (QueueEnum.eq.value, self.status)
