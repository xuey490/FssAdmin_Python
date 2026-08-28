from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.validator import email_validator, validate_required_code


class ConfigGroupSaveSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=2, max_length=100)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("配置组名称不能为空")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str):
        return validate_required_code(value)


class ConfigGroupUpdateSchema(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)


class ConfigSaveSchema(BaseModel):
    group_id: int | None = Field(default=None)
    key: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    value: str | None = Field(default=None)
    input_type: str | None = Field(default=None, max_length=32)
    config_select_data: Any = None
    sort: int = Field(default=0, ge=0)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("配置键不能为空")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("配置名称不能为空")
        return v


class ConfigUpdateSchema(BaseModel):
    group_id: int | None = None
    key: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    value: str | None = None
    input_type: str | None = Field(default=None, max_length=32)
    config_select_data: Any = None
    sort: int | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None, max_length=255)


class ConfigItemSchema(BaseModel):
    id: int
    value: Any = None


class ConfigBatchSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    config: list[ConfigItemSchema] = Field(
        default_factory=list,
        validation_alias=AliasChoices("config", "configs"),
    )


class ConfigTestEmailSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str = Field(..., validation_alias=AliasChoices("email", "to"))

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str):
        return email_validator(value)
