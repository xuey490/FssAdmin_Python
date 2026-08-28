from pydantic import BaseModel, Field, field_validator

from app.core.validator import validate_required_code


class PostCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="岗位名称")
    code: str = Field(..., min_length=2, max_length=100, description="岗位编码")
    sort: int = Field(default=0, ge=0, description="排序")
    status: int = Field(default=1, ge=0, le=1, description="状态")
    remark: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("岗位名称不能为空")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str):
        return validate_required_code(value)


class PostUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    code: str | None = Field(default=None, max_length=100)
    sort: int | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None):
        if value is None:
            return value
        v = value.strip()
        if not v:
            raise ValueError("岗位名称不能为空")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None):
        if not value or not str(value).strip():
            return value
        return validate_required_code(value)
