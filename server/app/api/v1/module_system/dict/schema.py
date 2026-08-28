from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.validator import validate_required_code


class DictTypeCreateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        ..., min_length=1, max_length=50,
        validation_alias=AliasChoices("name", "dict_name"),
    )
    code: str = Field(
        ..., min_length=2, max_length=100,
        validation_alias=AliasChoices("code", "dict_type"),
    )
    status: int = Field(default=1, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("字典名称不能为空")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str):
        return validate_required_code(value)


class DictTypeUpdateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None, max_length=50,
        validation_alias=AliasChoices("name", "dict_name"),
    )
    code: str | None = Field(
        default=None, max_length=100,
        validation_alias=AliasChoices("code", "dict_type"),
    )
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)


class DictDataCreateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type_id: int = Field(..., gt=0, description="字典类型ID")
    label: str = Field(
        ..., min_length=1, max_length=50,
        validation_alias=AliasChoices("label", "dict_label"),
    )
    value: str | None = Field(
        default=None, max_length=100,
        validation_alias=AliasChoices("value", "dict_value"),
    )
    color: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=100)
    sort: int = Field(default=0, ge=0)
    status: int = Field(default=1, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("字典标签不能为空")
        return v


class DictDataUpdateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type_id: int | None = Field(default=None, gt=0)
    label: str | None = Field(
        default=None, max_length=50,
        validation_alias=AliasChoices("label", "dict_label"),
    )
    value: str | None = Field(
        default=None, max_length=100,
        validation_alias=AliasChoices("value", "dict_value"),
    )
    color: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=100)
    sort: int | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)
