from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ArticleCreateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., min_length=1, max_length=255)
    category_id: int = Field(..., ge=1)
    author: str | None = Field(default=None, max_length=255)
    image: str | None = Field(default="", max_length=1000)
    describe: str = Field(..., min_length=1, max_length=1000)
    content: str | None = Field(default="")
    is_link: int = Field(default=2, ge=1, le=2)
    link_url: str | None = Field(default=None, max_length=255)
    is_hot: int = Field(default=2, ge=1, le=2)
    sort: int = Field(default=100, ge=0)
    status: int = Field(default=1, ge=0, le=1)
    summary: str | None = Field(default=None, max_length=500)
    cover_image: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    tags: str | None = Field(default=None, max_length=500)

    @field_validator("title", "describe")
    @classmethod
    def strip_required(cls, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise ValueError("不能为空")
        return v

    @model_validator(mode="after")
    def link_or_content(self):
        if self.is_link == 1:
            if not (self.link_url or "").strip():
                raise ValueError("外链地址不能为空")
        elif not (self.content or "").strip():
            raise ValueError("文章内容不能为空")
        return self


class ArticleUpdateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = Field(default=None, ge=1)
    author: str | None = Field(default=None, max_length=255)
    image: str | None = Field(default=None, max_length=1000)
    describe: str | None = Field(default=None, max_length=1000)
    content: str | None = Field(default=None)
    is_link: int | None = Field(default=None, ge=1, le=2)
    link_url: str | None = Field(default=None, max_length=255)
    is_hot: int | None = Field(default=None, ge=1, le=2)
    sort: int | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    summary: str | None = Field(default=None, max_length=500)
    cover_image: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    tags: str | None = Field(default=None, max_length=500)

    @field_validator("title", "describe")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        v = value.strip()
        if not v:
            raise ValueError("不能为空")
        return v

    @model_validator(mode="after")
    def link_or_content(self):
        if self.is_link == 1 and self.link_url is not None and not self.link_url.strip():
            raise ValueError("外链地址不能为空")
        if self.is_link == 2 and self.content is not None and not self.content.strip():
            raise ValueError("文章内容不能为空")
        return self
