from pydantic import BaseModel, Field, field_validator


class AttachmentUpdateSchema(BaseModel):
    origin_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("origin_name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("文件名不能为空")
        return v


class AttachmentMoveSchema(BaseModel):
    ids: list[int] = Field(..., min_length=1)
    category_id: int = Field(..., ge=0)

    @field_validator("ids", mode="before")
    @classmethod
    def split_ids(cls, value):
        if isinstance(value, str):
            return [int(x) for x in value.split(",") if x.strip()]
        if isinstance(value, int):
            return [value]
        return value


class AttachmentCategoryCreateSchema(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=100)
    parent_id: int = Field(default=0, ge=0)
    sort: int = Field(default=100, ge=0)
    status: int = Field(default=1, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("category_name")
    @classmethod
    def validate_name(cls, value: str):
        v = value.strip()
        if not v:
            raise ValueError("分类名称不能为空")
        return v


class AttachmentCategoryUpdateSchema(BaseModel):
    category_name: str | None = Field(default=None, max_length=100)
    parent_id: int | None = Field(default=None, ge=0)
    sort: int | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)
