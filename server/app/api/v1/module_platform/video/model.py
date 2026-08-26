from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, TenantMixin


class VideoModel(ModelMixin, TenantMixin):
    """platform_video — 视频元数据。

    status: 0=未获取 1=成功 -1=失败
    """

    __tablename__: str = "platform_video"
    __table_args__: dict[str, str] = {
        "comment": "视频元数据表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }
    # ponytail: 不默认 selectin downloads，避免 create/list 触发异步懒加载 MissingGreenlet
    __loader_options__: list[str] = []

    url: Mapped[str] = mapped_column(String(1000), nullable=False, comment="原始视频链接")
    title: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="标题")
    uploader: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="上传作者")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="视频描述")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="来源(youtube/bilibili等)")
    best_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最佳分辨率")
    thumbnail: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="缩略图URL")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="时长(秒)")
    info_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="yt-dlp瘦身快照(无直链)")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="元数据状态(0未获取1成功-1失败)")
    error_msg: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="元数据失败原因")
    local_dir: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="最近成功下载目录")
    active_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="当前活跃下载任务ID")

    downloads: Mapped[list["VideoDownloadModel"]] = relationship(
        "VideoDownloadModel",
        back_populates="video",
        lazy="noload",
        foreign_keys="VideoDownloadModel.video_id",
    )


class VideoDownloadModel(ModelMixin, TenantMixin):
    """platform_video_download — 下载队列任务。

    status: 0=queued 1=running 2=paused 3=done -1=failed -2=stopped
    """

    __tablename__: str = "platform_video_download"
    __table_args__: dict[str, str] = {
        "comment": "视频下载任务表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }
    __loader_options__: list[str] = []

    video_id: Mapped[int] = mapped_column(
        ForeignKey("platform_video.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联视频",
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="best", comment="best/custom/audio/subs")
    options_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="自定义下载选项")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="任务状态")
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="进度0-100")
    downloaded_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="已下载字节")
    total_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="总字节")
    speed: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="下载速度")
    eta: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="剩余秒数")
    error_msg: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="失败/停止原因")
    local_dir: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="本次输出目录")
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="优先级(越大越先)")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")

    video: Mapped["VideoModel"] = relationship(
        "VideoModel",
        back_populates="downloads",
        foreign_keys=[video_id],
        lazy="noload",
    )
