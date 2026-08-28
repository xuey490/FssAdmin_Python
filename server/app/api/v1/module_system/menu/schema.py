from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validator import menu_request_validator, validate_required_code


class MenuCreateSchema(BaseModel):
    """菜单创建（对齐 sa_system_menu）。"""

    name: str | None = Field(default=None, max_length=64, description="菜单名称")
    code: str | None = Field(default=None, max_length=64, description="编码")
    slug: str | None = Field(default=None, max_length=100, description="权限标识")
    type: int = Field(default=1, ge=1, le=4, description="1目录 2菜单 3按钮 4外链")
    parent_id: int = Field(default=0, ge=0, description="父菜单ID")
    path: str | None = Field(default=None, max_length=255, description="路由路径")
    component: str | None = Field(default=None, max_length=255, description="组件路径")
    method: str | None = Field(default=None, max_length=10, description="请求方法")
    icon: str | None = Field(default=None, max_length=64, description="图标")
    sort: int = Field(default=100, ge=0, description="排序")
    link_url: str | None = Field(default=None, max_length=255, description="外链地址")
    is_iframe: int = Field(default=2, ge=1, le=2)
    is_keep_alive: int = Field(default=2, ge=1, le=2)
    is_hidden: int = Field(default=2, ge=1, le=2)
    is_fixed_tab: int = Field(default=2, ge=1, le=2)
    is_full_page: int = Field(default=2, ge=1, le=2)
    status: int = Field(default=1, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)

    @model_validator(mode="after")
    def validate_type_fields(self):
        return menu_request_validator(self)


class MenuUpdateSchema(BaseModel):
    """菜单更新"""

    name: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=64)
    slug: str | None = Field(default=None, max_length=100)
    type: int | None = Field(default=None, ge=1, le=4)
    parent_id: int | None = Field(default=None, ge=0)
    path: str | None = Field(default=None, max_length=255)
    component: str | None = Field(default=None, max_length=255)
    method: str | None = Field(default=None, max_length=10)
    icon: str | None = Field(default=None, max_length=64)
    sort: int | None = Field(default=None, ge=0)
    link_url: str | None = Field(default=None, max_length=255)
    is_iframe: int | None = Field(default=None, ge=1, le=2)
    is_keep_alive: int | None = Field(default=None, ge=1, le=2)
    is_hidden: int | None = Field(default=None, ge=1, le=2)
    is_fixed_tab: int | None = Field(default=None, ge=1, le=2)
    is_full_page: int | None = Field(default=None, ge=1, le=2)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type is None:
            return self
        return menu_request_validator(self)
