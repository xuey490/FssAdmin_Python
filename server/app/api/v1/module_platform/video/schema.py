from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam
from app.core.base_schema import BaseSchema, TenantBySchema


class VideoCreateSchema(BaseModel):
    """批量创建视频链接。"""

    urls: list[str] = Field(..., min_length=1, description="视频链接列表")
    enqueue: bool = Field(default=False, description="是否加入下载队列")


class VideoUpdateSchema(BaseModel):
    """更新视频链接。"""

    url: str = Field(..., min_length=1, max_length=1000, description="视频链接")


class VideoDownloadCreateSchema(BaseModel):
    """创建下载任务。"""

    mode: Literal["best", "custom", "audio", "subs"] = Field(default="best", description="下载模式")
    format_id: str | None = Field(default=None, description="视频格式ID")
    audio_format: str | None = Field(default=None, description="音频格式(mp3/m4a等)")
    height: int | None = Field(default=None, ge=144, description="最大分辨率高度")
    sub_langs: str | None = Field(default=None, description="字幕语言，如 zh-Hans,en")


class JobOutSchema(BaseSchema, TenantBySchema):
    """下载任务响应。"""

    model_config = ConfigDict(from_attributes=True)

    video_id: int
    mode: str
    options_json: dict[str, Any] | None = None
    status: int
    progress: float = 0
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed: str | None = None
    eta: int | None = None
    error_msg: str | None = None
    local_dir: str | None = None
    priority: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    video_title: str | None = None
    video_url: str | None = None


class VideoOutSchema(BaseSchema, TenantBySchema):
    """视频列表/详情响应。"""

    model_config = ConfigDict(from_attributes=True)

    url: str
    title: str | None = None
    uploader: str | None = None
    description: str | None = None
    source: str | None = None
    best_resolution: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    status: int = 0
    error_msg: str | None = None
    local_dir: str | None = None
    active_job_id: int | None = None
    active_job_status: int | None = None  # 当前活跃任务状态（暂停/继续用）
    # mode=best 的下载任务摘要（列表「下载进度」列只看 best）
    job_status: int | None = None
    job_progress: float | None = None
    job_speed: str | None = None
    job_mode: str | None = None
    job_error_msg: str | None = None
    job_local_dir: str | None = None


class FormatItemSchema(BaseModel):
    format_id: str
    ext: str | None = None
    resolution: str | None = None
    vcodec: str | None = None
    acodec: str | None = None
    filesize: int | None = None
    note: str | None = None


class PreviewQualitySchema(BaseModel):
    label: str
    height: int | None = None
    url: str
    format_id: str | None = None


class PreviewOutSchema(BaseModel):
    stream_url: str = ""
    page_url: str
    thumbnail: str | None = None
    title: str | None = None
    qualities: list[PreviewQualitySchema] = []


class LocalFileItemSchema(BaseModel):
    name: str
    size: int = 0
    mtime: str | None = None
    ext: str | None = None
    url: str | None = None  # /static/videos/... 可直接访问


class LocalFilesOutSchema(BaseModel):
    local_dir: str | None = None
    title: str | None = None
    files: list[LocalFileItemSchema] = []


class ProgressItemSchema(BaseModel):
    """轻量进度/元数据快照（供列表原地刷新）。"""

    video_id: int
    # 元数据
    status: int | None = None
    title: str | None = None
    uploader: str | None = None
    source: str | None = None
    best_resolution: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    error_msg: str | None = None
    # 下载：job_* 仅 mode=best；active_job_* 供暂停/继续
    active_job_id: int | None = None
    active_job_status: int | None = None
    job_status: int | None = None
    job_progress: float | None = None
    job_speed: str | None = None
    job_mode: str | None = None
    job_error_msg: str | None = None
    job_local_dir: str | None = None
    local_dir: str | None = None


@dataclass
class VideoQueryParam(BaseQueryParam):
    title: str | None = Query(None, description="标题")
    uploader: str | None = Query(None, description="作者")
    source: str | None = Query(None, description="来源")
    status: int | None = Query(None, description="元数据状态")

    def __post_init__(self) -> None:
        if self.title:
            self.title = (QueueEnum.like.value, self.title)
        if self.uploader:
            self.uploader = (QueueEnum.like.value, self.uploader)
        if self.source:
            self.source = (QueueEnum.eq.value, self.source)
        if self.status is not None:
            self.status = (QueueEnum.eq.value, self.status)


@dataclass
class DownloadQueueQueryParam(BaseQueryParam):
    status: int | None = Query(None, description="任务状态")
    video_id: int | None = Query(None, description="视频ID")

    def __post_init__(self) -> None:
        if self.status is not None:
            self.status = (QueueEnum.eq.value, self.status)
        if self.video_id is not None:
            self.video_id = (QueueEnum.eq.value, self.video_id)
