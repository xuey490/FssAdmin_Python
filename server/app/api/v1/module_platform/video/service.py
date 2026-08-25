"""视频管理业务逻辑。"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.config.path_conf import BASE_DIR
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.core.logger import logger

from .constants import (
    CTRL_PAUSE,
    CTRL_RUN,
    CTRL_STOP,
    JOB_DONE,
    JOB_FAILED,
    JOB_PAUSED,
    JOB_QUEUED,
    JOB_RUNNING,
    JOB_STOPPED,
    META_FAIL,
    META_OK,
    META_PENDING,
)

BEST_MODE = "best"
from .crud import VideoCRUD, VideoDownloadCRUD
from .downloader import DownloadQueue
from .model import VideoDownloadModel, VideoModel
from .schema import (
    DownloadQueueQueryParam,
    FormatItemSchema,
    JobOutSchema,
    LocalFileItemSchema,
    LocalFilesOutSchema,
    PreviewOutSchema,
    PreviewQualitySchema,
    ProgressItemSchema,
    VideoCreateSchema,
    VideoDownloadCreateSchema,
    VideoOutSchema,
    VideoQueryParam,
    VideoUpdateSchema,
)
from .ytdlp_util import (
    extract_info,
    get_best_stream_url,
    get_format_stream_url,
    is_risk_control_error,
    list_formats,
    list_video_qualities,
    normalize_meta,
    resolve_input_urls,
)


def _parse_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls:
        for line in str(raw).splitlines():
            u = line.strip()
            if not u or u.startswith("#"):
                continue
            if u in seen:
                continue
            seen.add(u)
            out.append(u)
    return out


def _stream_headers(page_url: str) -> dict[str, str]:
    """CDN 常校验 Referer/UA；缺了会直接掐连接。"""
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    referer = "https://www.bilibili.com/"
    low = (page_url or "").lower()
    if "youtube.com" in low or "youtu.be" in low:
        referer = "https://www.youtube.com/"
    elif page_url:
        from urllib.parse import urlparse

        p = urlparse(page_url)
        if p.scheme and p.netloc:
            referer = f"{p.scheme}://{p.netloc}/"
    return {
        "User-Agent": ua,
        "Referer": referer,
        "Origin": referer.rstrip("/"),
    }


class VideoService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.video_crud = VideoCRUD(auth)
        self.job_crud = VideoDownloadCRUD(auth)

    def _tenant_id(self) -> int:
        return int(self.auth.tenant_id or getattr(self.auth.user, "tenant_id", None) or 1)

    async def _to_out(
        self, video: VideoModel, job: VideoDownloadModel | None = None
    ) -> VideoOutSchema:
        """组装列表/详情；禁止访问 video.downloads（async 下会 MissingGreenlet）。"""
        data = VideoOutSchema.model_validate(video)
        await self._apply_best_job_fields(data, video.id)
        # 暂停/继续/停止看当前活跃任务（可能不是 best）
        active = job
        if active is None and video.active_job_id and self.auth.db is not None:
            active = await self.auth.db.get(VideoDownloadModel, video.active_job_id)
        if active:
            data.active_job_id = active.id
            data.active_job_status = active.status
        return data

    async def _latest_best_jobs(self, video_ids: list[int]) -> dict[int, VideoDownloadModel]:
        """每个视频最新一条 mode=best 的下载任务。"""
        if not video_ids or self.auth.db is None:
            return {}
        q = await self.auth.db.execute(
            select(VideoDownloadModel)
            .where(
                VideoDownloadModel.video_id.in_(video_ids),
                VideoDownloadModel.mode == BEST_MODE,
                VideoDownloadModel.delete_time.is_(None),
            )
            .order_by(VideoDownloadModel.id.desc())
        )
        out: dict[int, VideoDownloadModel] = {}
        for row in q.scalars().all():
            if row.video_id not in out:
                out[row.video_id] = row
        return out

    def _fill_best_job_fields(self, target, best: VideoDownloadModel | None) -> None:
        """列表「下载进度」：只展示该 best 任务的 progress。"""
        if not best:
            return
        cache = DownloadQueue.instance().get_progress_cache(best.id)
        # 进行中优先 Redis 热进度，否则用库里的 progress
        progress = (
            float(cache["progress"])
            if cache and "progress" in cache
            else float(best.progress or 0)
        )
        speed = (cache or {}).get("speed") or best.speed
        status = best.status
        # 仅真正完成才打满；暂停/进行中即使 progress 异常也不冒充完成
        if status == JOB_DONE:
            progress = 100.0
            speed = None
        target.job_status = status
        target.job_progress = progress
        target.job_speed = speed
        target.job_mode = best.mode
        target.job_error_msg = best.error_msg
        target.job_local_dir = best.local_dir

    async def _get_best_job(self, video_id: int) -> VideoDownloadModel | None:
        jobs = await self._latest_best_jobs([video_id])
        return jobs.get(video_id)

    async def _apply_best_job_fields(self, target, video_id: int) -> None:
        self._fill_best_job_fields(target, await self._get_best_job(video_id))

    async def get_list(
        self,
        *,
        page_no: int,
        page_size: int,
        order_by: list[dict] | None = None,
        search: VideoQueryParam | None = None,
    ) -> tuple[list[VideoOutSchema], int]:
        raw = vars(search) if search else {}
        search_dict = {
            k: v
            for k, v in raw.items()
            if k in ("title", "uploader", "source", "status") and v is not None
        }
        result = await self.video_crud.page(
            search=search_dict,
            order_by=order_by or [{"id": "desc"}],
            offset=(page_no - 1) * page_size,
            limit=page_size,
            preload=[],
        )
        best_map = await self._latest_best_jobs([v.id for v in result.items])
        items: list[VideoOutSchema] = []
        for v in result.items:
            data = VideoOutSchema.model_validate(v)
            self._fill_best_job_fields(data, best_map.get(v.id))
            if v.active_job_id and self.auth.db is not None:
                active = await self.auth.db.get(VideoDownloadModel, v.active_job_id)
                if active:
                    data.active_job_id = active.id
                    data.active_job_status = active.status
            items.append(data)
        return items, result.total

    async def progress_snapshot(self, video_ids: list[int]) -> list[ProgressItemSchema]:
        """仅返回指定视频的元数据+下载进度，供前端原地 patch。"""
        if not video_ids or self.auth.db is None:
            return []
        q = await self.auth.db.execute(
            select(VideoModel).where(
                VideoModel.id.in_(video_ids),
                VideoModel.delete_time.is_(None),
            )
        )
        videos = list(q.scalars().all())
        best_map = await self._latest_best_jobs([v.id for v in videos])
        out: list[ProgressItemSchema] = []
        for video in videos:
            item = ProgressItemSchema(
                video_id=video.id,
                status=video.status,
                title=video.title,
                uploader=video.uploader,
                source=video.source,
                best_resolution=video.best_resolution,
                thumbnail=video.thumbnail,
                duration=video.duration,
                error_msg=video.error_msg,
                active_job_id=video.active_job_id,
                local_dir=video.local_dir,
            )
            self._fill_best_job_fields(item, best_map.get(video.id))
            if video.active_job_id:
                active = await self.auth.db.get(VideoDownloadModel, video.active_job_id)
                if active:
                    item.active_job_status = active.status
            out.append(item)
        return out

    async def detail(self, video_id: int) -> VideoOutSchema:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在", preload=[])
        return await self._to_out(video)

    async def _fill_meta(self, video: VideoModel) -> VideoModel:
        try:
            info = await asyncio.to_thread(extract_info, video.url)
            meta = normalize_meta(info, video.url)
            video.title = meta.get("title")
            video.uploader = meta.get("uploader")
            video.description = meta.get("description")
            video.source = meta.get("source")
            video.best_resolution = meta.get("best_resolution")
            video.thumbnail = meta.get("thumbnail")
            video.duration = meta.get("duration")
            video.url = meta.get("url") or video.url
            video.info_json = meta.get("info_json")
            video.status = META_OK
            video.error_msg = None
        except Exception as e:
            logger.warning("extract_info failed url={} err={}", video.url, e)
            video.status = META_FAIL
            video.error_msg = str(e)[:500]
            if is_risk_control_error(e):
                # 风控：只保留原始链接
                video.title = None
                video.uploader = None
                video.description = None
                video.source = None
                video.best_resolution = None
                video.thumbnail = None
                video.duration = None
                video.info_json = None
        await self.auth.db.flush()  # type: ignore[union-attr]
        return video

    async def _existing_urls(self, urls: list[str], tenant_id: int) -> set[str]:
        """当前租户下未删除的已存在 url。"""
        if not urls or self.auth.db is None:
            return set()
        q = await self.auth.db.execute(
            select(VideoModel.url).where(
                VideoModel.tenant_id == tenant_id,
                VideoModel.url.in_(urls),
                VideoModel.delete_time.is_(None),
            )
        )
        return set(q.scalars().all())

    async def create(
        self, data: VideoCreateSchema
    ) -> tuple[list[VideoOutSchema], list[tuple[int, bool]], int]:
        """快速入库 status=0；已存在链接跳过解析/入库；合集展开后去重。

        返回 (新建列表, 待拉元数据, 跳过条数)。
        """
        raw = _parse_urls(data.urls)
        if not raw:
            raise CustomException(msg="请输入至少一个有效链接")
        tenant_id = self._tenant_id()

        # 原始链接已在库 → 跳过 flat 解析
        existing_raw = await self._existing_urls(raw, tenant_id)
        to_resolve = [u for u in raw if u not in existing_raw]
        skipped = len(raw) - len(to_resolve)

        resolved: list[str] = []
        if to_resolve:
            resolved = await asyncio.to_thread(resolve_input_urls, to_resolve)

        # 展开后的 webpage_url 再滤一轮已存在
        if resolved:
            existing_resolved = await self._existing_urls(resolved, tenant_id)
            new_urls = [u for u in resolved if u not in existing_resolved]
            skipped += len(resolved) - len(new_urls)
        else:
            new_urls = []

        if not new_urls:
            if skipped:
                # 全部已存在：按成功跳过返回，勿抛异常（否则前端收到 500）
                return [], [], skipped
            raise CustomException(msg="未能解析出有效视频地址（合集可能为空）")

        results: list[VideoOutSchema] = []
        pending: list[tuple[int, bool]] = []
        for url in new_urls:
            obj = VideoModel(
                url=url,
                status=META_PENDING,
                tenant_id=tenant_id,
            )
            self.auth.db.add(obj)  # type: ignore[union-attr]
            await self.auth.db.flush()  # type: ignore[union-attr]
            pending.append((obj.id, data.enqueue))
            results.append(await self._to_out(obj))
        await self.auth.db.flush()  # type: ignore[union-attr]
        return results, pending, skipped

    async def update(self, video_id: int, data: VideoUpdateSchema) -> VideoOutSchema:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在", preload=[])
        video.url = data.url.strip()
        video.status = META_PENDING
        video.error_msg = None
        video.title = None
        video.uploader = None
        video.description = None
        video.source = None
        video.best_resolution = None
        video.thumbnail = None
        video.duration = None
        video.info_json = None
        await self.auth.db.flush()  # type: ignore[union-attr]
        return await self._to_out(video)

    async def refresh(self, video_id: int) -> VideoOutSchema:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在", preload=[])
        video.status = META_PENDING
        video.error_msg = None
        await self.auth.db.flush()  # type: ignore[union-attr]
        return await self._to_out(video)

    async def delete(self, video_id: int) -> None:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在")
        local_dir = video.local_dir
        # 软删关联 jobs
        jobs = await self.job_crud.get_list(search={"video_id": video_id})
        now = datetime.now()
        for job in jobs:
            job.delete_time = now
            if job.status in (JOB_QUEUED, JOB_RUNNING):
                DownloadQueue.instance().set_ctrl(job.id, CTRL_STOP)
                job.status = JOB_STOPPED
        video.delete_time = now
        video.active_job_id = None
        await self.auth.db.flush()  # type: ignore[union-attr]
        if local_dir:
            try:
                shutil.rmtree(local_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("remove local_dir failed: {}", e)

    async def _create_job(
        self,
        video: VideoModel,
        *,
        mode: str,
        options: dict[str, Any] | None,
    ) -> VideoDownloadModel:
        job = VideoDownloadModel(
            video_id=video.id,
            tenant_id=video.tenant_id,
            mode=mode,
            options_json=options,
            status=JOB_QUEUED,
            progress=0.0,
        )
        self.auth.db.add(job)  # type: ignore[union-attr]
        await self.auth.db.flush()  # type: ignore[union-attr]
        return job

    async def enqueue_download(self, video_id: int, data: VideoDownloadCreateSchema) -> JobOutSchema:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在")
        if video.status != META_OK:
            raise CustomException(msg="请先成功获取视频信息后再下载")
        options: dict[str, Any] = {}
        if data.format_id:
            options["format_id"] = data.format_id
        if data.audio_format:
            options["audio_format"] = data.audio_format
        if data.height:
            options["height"] = data.height
        if data.sub_langs:
            options["sub_langs"] = data.sub_langs
        job = await self._create_job(video, mode=data.mode, options=options or None)
        video.active_job_id = job.id
        await self.auth.db.flush()  # type: ignore[union-attr]
        DownloadQueue.instance().kick()
        return JobOutSchema.model_validate(job)

    async def queue_list(
        self,
        *,
        page_no: int,
        page_size: int,
        search: DownloadQueueQueryParam | None = None,
    ) -> tuple[list[JobOutSchema], int]:
        raw = vars(search) if search else {}
        search_dict = {k: v for k, v in raw.items() if k in ("status", "video_id") and v is not None}
        result = await self.job_crud.page(
            search=search_dict,
            order_by=[{"id": "desc"}],
            offset=(page_no - 1) * page_size,
            limit=page_size,
        )
        items: list[JobOutSchema] = []
        for job in result.items:
            out = JobOutSchema.model_validate(job)
            if self.auth.db is not None:
                video = await self.auth.db.get(VideoModel, job.video_id)
                if video:
                    out.video_title = video.title
                    out.video_url = video.url
            cache = DownloadQueue.instance().get_progress_cache(job.id)
            if cache and job.status == JOB_RUNNING:
                out.progress = float(cache.get("progress") or out.progress)
                out.speed = cache.get("speed") or out.speed
                out.eta = cache.get("eta") if cache.get("eta") is not None else out.eta
            items.append(out)
        return items, result.total

    async def pause_job(self, job_id: int) -> JobOutSchema:
        job = await self.job_crud.get_or_404(id=job_id, msg="任务不存在")
        if job.status == JOB_QUEUED:
            job.status = JOB_PAUSED
            job.error_msg = "排队中暂停"
            await self.auth.db.flush()  # type: ignore[union-attr]
        elif job.status == JOB_RUNNING:
            DownloadQueue.instance().set_ctrl(job_id, CTRL_PAUSE)
            # 工人 hook 会落库 paused；此处先写 ctrl
        else:
            raise CustomException(msg="当前状态不可暂停")
        return JobOutSchema.model_validate(job)

    async def resume_job(self, job_id: int) -> JobOutSchema:
        job = await self.job_crud.get_or_404(id=job_id, msg="任务不存在")
        if job.status not in (JOB_PAUSED, JOB_FAILED, JOB_STOPPED, JOB_DONE):
            raise CustomException(msg="当前状态不可继续")
        job.status = JOB_QUEUED
        job.error_msg = None
        job.finished_at = None
        video = await self.video_crud.get(id=job.video_id)
        if video:
            video.active_job_id = job.id
        DownloadQueue.instance().set_ctrl(job_id, CTRL_RUN)
        await self.auth.db.flush()  # type: ignore[union-attr]
        DownloadQueue.instance().kick()
        return JobOutSchema.model_validate(job)

    async def stop_job(self, job_id: int) -> JobOutSchema:
        job = await self.job_crud.get_or_404(id=job_id, msg="任务不存在")
        if job.status == JOB_RUNNING:
            DownloadQueue.instance().set_ctrl(job_id, CTRL_STOP)
        elif job.status in (JOB_QUEUED, JOB_PAUSED):
            job.status = JOB_STOPPED
            job.error_msg = "用户停止"
            job.finished_at = datetime.now()
            video = await self.video_crud.get(id=job.video_id)
            if video and video.active_job_id == job.id:
                video.active_job_id = None
            await self.auth.db.flush()  # type: ignore[union-attr]
        else:
            raise CustomException(msg="当前状态不可停止")
        return JobOutSchema.model_validate(job)

    async def pause_all(self) -> int:
        # queued → paused；running → ctrl pause（由工人落库 paused，保留真实 progress）
        db = self.auth.db
        assert db is not None
        q = await db.execute(
            select(VideoDownloadModel).where(
                VideoDownloadModel.delete_time.is_(None),
                VideoDownloadModel.status.in_([JOB_QUEUED, JOB_RUNNING]),
            )
        )
        rows = list(q.scalars().all())
        n = 0
        for job in rows:
            if job.status == JOB_QUEUED:
                job.status = JOB_PAUSED
                job.error_msg = "全局暂停"
                DownloadQueue.instance().set_ctrl(job.id, CTRL_PAUSE)
                n += 1
            elif job.status == JOB_RUNNING:
                DownloadQueue.instance().set_ctrl(job.id, CTRL_PAUSE)
                n += 1
        await db.flush()
        return n

    async def resume_all(self) -> int:
        db = self.auth.db
        assert db is not None
        # 1) 已暂停 → 重新排队
        q = await db.execute(
            select(VideoDownloadModel).where(
                VideoDownloadModel.delete_time.is_(None),
                VideoDownloadModel.status == JOB_PAUSED,
            )
        )
        paused = list(q.scalars().all())
        for job in paused:
            job.status = JOB_QUEUED
            job.error_msg = None
            job.finished_at = None
            DownloadQueue.instance().set_ctrl(job.id, CTRL_RUN)
            if self.auth.db is not None:
                video = await self.auth.db.get(VideoModel, job.video_id)
                if video:
                    video.active_job_id = job.id
        # 2) 仍在 running 但已发过暂停信号 → 取消暂停，让当前工人继续
        q2 = await db.execute(
            select(VideoDownloadModel).where(
                VideoDownloadModel.delete_time.is_(None),
                VideoDownloadModel.status == JOB_RUNNING,
            )
        )
        running = list(q2.scalars().all())
        cancelled_pause = 0
        for job in running:
            if DownloadQueue.instance().get_ctrl(job.id) == CTRL_PAUSE:
                DownloadQueue.instance().set_ctrl(job.id, CTRL_RUN)
                cancelled_pause += 1
        await db.flush()
        DownloadQueue.instance().kick()
        return len(paused) + cancelled_pause

    async def formats(self, video_id: int) -> list[FormatItemSchema]:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在")
        try:
            items = await asyncio.to_thread(list_formats, video.url)
        except Exception as e:
            raise CustomException(msg=f"获取格式失败: {e}") from e
        return [FormatItemSchema.model_validate(i) for i in items]

    async def list_local_files(self, video_id: int) -> LocalFilesOutSchema:
        """列出 platform_video.local_dir 下已下载文件（限制在 VIDEO_DOWNLOAD_ROOT 内）。"""
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在", preload=[])
        if not video.local_dir:
            return LocalFilesOutSchema(local_dir=None, title=video.title, files=[])

        root = Path(settings.VIDEO_DOWNLOAD_ROOT)
        if not root.is_absolute():
            root = (BASE_DIR / root).resolve()
        else:
            root = root.resolve()
        static_root = Path(settings.STATIC_ROOT).resolve()

        d = Path(video.local_dir)
        if not d.is_absolute():
            d = (BASE_DIR / d).resolve()
        else:
            d = d.resolve()

        try:
            d.relative_to(root)
        except ValueError as e:
            raise CustomException(msg="下载目录不在允许范围内") from e

        if not d.is_dir():
            return LocalFilesOutSchema(local_dir=str(d), title=video.title, files=[])

        media_ext = {
            ".mp4",
            ".webm",
            ".mkv",
            ".avi",
            ".mov",
            ".flv",
            ".m4a",
            ".mp3",
            ".opus",
            ".ogg",
            ".wav",
            ".vtt",
            ".srt",
            ".ass",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }
        files: list[LocalFileItemSchema] = []
        for p in sorted(d.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_file():
                continue
            if p.name.startswith(".") or p.suffix.lower() == ".part":
                continue
            ext = p.suffix.lower()
            if ext and ext not in media_ext:
                # 仍列出其它文件，方便排查；前端可按需过滤
                pass
            st = p.stat()
            url: str | None = None
            try:
                rel = p.resolve().relative_to(static_root)
                url = f"{settings.STATIC_URL.rstrip('/')}/{rel.as_posix()}"
            except ValueError:
                url = None
            files.append(
                LocalFileItemSchema(
                    name=p.name,
                    size=int(st.st_size),
                    mtime=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    ext=ext.lstrip(".") or None,
                    url=url,
                )
            )
        return LocalFilesOutSchema(local_dir=str(d), title=video.title, files=files)

    async def preview(self, video_id: int) -> PreviewOutSchema:
        """返回代理流地址 + 原页面 + 清晰度列表（播放走 /stream?access_token=）。"""
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在")
        qualities: list[dict] = []
        try:
            raw = await asyncio.to_thread(list_video_qualities, video.url)
            qualities = [
                {
                    "label": q["label"],
                    "height": q.get("height"),
                    "format_id": q.get("format_id") or None,
                    "url": "",  # 前端拼代理地址，不把 CDN 直链交给播放器
                }
                for q in raw
            ]
        except Exception as e:
            logger.warning("preview qualities failed id={} err={}", video_id, e)
        return PreviewOutSchema(
            stream_url=f"/platform/video/stream/{video_id}",
            page_url=video.url,
            thumbnail=video.thumbnail,
            title=video.title,
            qualities=[PreviewQualitySchema.model_validate(q) for q in qualities],
        )

    async def stream(self, video_id: int, format_id: str | None = None) -> StreamingResponse:
        video = await self.video_crud.get_or_404(id=video_id, msg="视频不存在")
        try:
            if format_id:
                media_url = await asyncio.to_thread(get_format_stream_url, video.url, format_id)
            else:
                media_url = await asyncio.to_thread(get_best_stream_url, video.url)
        except Exception as e:
            raise CustomException(msg=f"获取播放地址失败: {e}") from e

        headers = _stream_headers(video.url)
        # 先建上游连接再开始推流：失败可返回业务错误，避免 ASGI 中途 ConnectError 崩掉
        # 本地代理常能解 bilibili API，但拉 *.bilivideo.cn 会 TLS 失败 → 再试直连
        client: httpx.AsyncClient | None = None
        resp: httpx.Response | None = None
        last_err: BaseException | None = None
        for trust_env in (True, False):
            c = httpx.AsyncClient(
                follow_redirects=True,
                timeout=60.0,
                headers=headers,
                trust_env=trust_env,
            )
            try:
                r = await c.send(c.build_request("GET", media_url), stream=True)
                r.raise_for_status()
                client, resp = c, r
                break
            except Exception as e:
                last_err = e
                logger.warning(
                    "stream upstream failed trust_env={} video_id={} err={}",
                    trust_env,
                    video_id,
                    e,
                )
                await c.aclose()

        if client is None or resp is None:
            raise CustomException(msg=f"拉取媒体流失败: {last_err}") from last_err

        media_type = resp.headers.get("content-type") or "video/mp4"

        async def gen():
            try:
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    yield chunk
            except Exception as e:
                logger.warning("stream pump aborted video_id={} err={}", video_id, e)
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(gen(), media_type=media_type)
