from pydantic import BaseModel, Field, field_validator

from app.core.validator import DateTimeStr, email_validator, phone_validator, validate_required_code


class TenantCreateSchema(BaseModel):
    tenant_name: str = Field(..., min_length=1, max_length=100, description="租户名称")
    tenant_code: str = Field(..., min_length=2, max_length=50, description="租户编码")
    contact_name: str | None = Field(default=None, max_length=50)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_email: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1, ge=0, le=1)
    expire_time: DateTimeStr | None = Field(default=None)
    max_users: int = Field(default=0, ge=0)
    max_depts: int = Field(default=0, ge=0)
    max_roles: int = Field(default=0, ge=0)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("tenant_name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("租户名称不能为空")
        return v

    @field_validator("tenant_code")
    @classmethod
    def validate_code(cls, value: str):
        return validate_required_code(value)

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None):
        return phone_validator(value)

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, value: str | None):
        if not value:
            return value
        return email_validator(value)


class TenantUpdateSchema(BaseModel):
    tenant_name: str | None = Field(default=None, min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, max_length=50)
    contact_name: str | None = Field(default=None, max_length=50)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_email: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=255)
    status: int | None = Field(default=None, ge=0, le=1)
    expire_time: DateTimeStr | None = Field(default=None)
    max_users: int | None = Field(default=None, ge=0)
    max_depts: int | None = Field(default=None, ge=0)
    max_roles: int | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("tenant_code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None):
        return phone_validator(value)

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, value: str | None):
        if not value:
            return value
        return email_validator(value)


class TenantUsersSchema(BaseModel):
    user_ids: list[int] = Field(default_factory=list)


class TenantFlagSchema(BaseModel):
    is_super: int = Field(default=0, ge=0, le=1)


class TenantDefaultSchema(BaseModel):
    is_default: int = Field(default=0, ge=0, le=1)
