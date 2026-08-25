"""元数据拉取队列：创建只入库 status=0，后台逐条 yt-dlp 取信息。"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import select, update

from app.config.setting import settings
from app.core.database import db_session
from app.core.logger import logger

from .constants import JOB_QUEUED, META_FAIL, META_OK, META_PENDING, REDIS_META_QUEUE
from .model import VideoDownloadModel, VideoModel
from .ytdlp_util import extract_info, is_risk_control_error, normalize_meta


class MetaFetchQueue:
    """Redis 列表（或内存队列）+ 线程池，逐条拉取视频元数据。"""

    _instance: MetaFetchQueue | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._active: set[int] = set()
        self._active_lock = threading.Lock()
        # _inflight 包含 submit 后、真正开始处理前的 worker，空队列不能据此无限补 worker。
        self._inflight = 0
        self._redis = None
        self._mem: list[str] = []
        self._mem_cond = threading.Condition()
        self._started = False
        self._stop_event = threading.Event()

    @classmethod
    def instance(cls) -> MetaFetchQueue:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_redis(self):
        if self._redis is not None:
            return self._redis if self._redis is not False else None
        if not settings.REDIS_ENABLE:
            return None
        try:
            import redis

            auth_kwargs: dict[str, Any] = {}
            if settings.REDIS_PASSWORD:
                auth_kwargs["password"] = settings.REDIS_PASSWORD
            if settings.REDIS_USER:
                auth_kwargs["username"] = settings.REDIS_USER
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=int(settings.REDIS_DB_NAME),
                decode_responses=True,
                **auth_kwargs,
            )
            client.ping()
            self._redis = client
            return client
        except Exception as e:
            logger.warning("video meta redis unavailable, use memory queue: {}", e)
            self._redis = False  # type: ignore[assignment]
            return None

    def enqueue(self, video_id: int, *, enqueue_download: bool = False) -> None:
        payload = json.dumps({"id": int(video_id), "enqueue": bool(enqueue_download)})
        rd = self._get_redis()
        if rd:
            rd.lpush(REDIS_META_QUEUE, payload)
        else:
            with self._mem_cond:
                self._mem.append(payload)
                self._mem_cond.notify()
        self.kick()

    def enqueue_many(self, items: list[tuple[int, bool]]) -> None:
        for video_id, enqueue_download in items:
            self.enqueue(video_id, enqueue_download=enqueue_download)

    def start(self) -> None:
        if self._started:
            return
        self._stop_event.clear()
        workers = max(1, int(getattr(settings, "VIDEO_META_WORKERS", None) or 1))
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="video-meta")
        self._started = True
        recovered = 0
        if getattr(settings, "VIDEO_META_RECOVER_ON_START", False):
            recovered = self.recover_pending()
        else:
            dropped = self._drop_leftover_queue()
            if dropped:
                logger.info(
                    "dropped leftover meta queue items={} (VIDEO_META_RECOVER_ON_START=false)",
                    dropped,
                )
        logger.info(
            "MetaFetchQueue started workers={} recover_on_start={} recovered={}",
            workers,
            bool(getattr(settings, "VIDEO_META_RECOVER_ON_START", False)),
            recovered,
        )
        if recovered:
            self.kick()

    def stop(self) -> None:
        self._stop_event.set()
        self._started = False
        with self._mem_cond:
            self._mem_cond.notify_all()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
        with self._active_lock:
            self._inflight = 0
        logger.info("MetaFetchQueue stopped")

    def _drop_leftover_queue(self) -> int:
        """启动且不恢复时丢掉上次进程留在 Redis/内存里的待拉任务，避免下次 enqueue 时一次性引爆。"""
        rd = self._get_redis()
        if rd:
            n = int(rd.llen(REDIS_META_QUEUE) or 0)
            if n:
                rd.delete(REDIS_META_QUEUE)
            return n
        with self._mem_cond:
            n = len(self._mem)
            self._mem.clear()
            return n

    def recover_pending(self) -> int:
        """把 DB 中仍为未获取的视频重新入队。默认不在启动时调用（避免闲时 yt-dlp 把 RSS 打满）。"""
        with db_session() as db:
            rows = db.execute(
                select(VideoModel.id).where(
                    VideoModel.status == META_PENDING,
                    VideoModel.delete_time.is_(None),
                )
            ).scalars().all()
            ids = [int(x) for x in rows]
        for vid in ids:
            self.enqueue(vid, enqueue_download=False)
        return len(ids)

    def kick(self) -> None:
        if not self._started or not self._executor or self._stop_event.is_set():
            return
        workers = max(1, int(getattr(settings, "VIDEO_META_WORKERS", None) or 1))
        with self._active_lock:
            slots = max(0, workers - self._inflight)
            self._inflight += slots
        for _ in range(max(0, slots)):
            try:
                self._executor.submit(self._worker_once)
            except Exception:
                with self._active_lock:
                    self._inflight -= 1
                raise

    def _pop_payload(self) -> str | None:
        rd = self._get_redis()
        if rd:
            # 非阻塞；kick 循环拉
            item = rd.rpop(REDIS_META_QUEUE)
            return str(item) if item else None
        with self._mem_cond:
            if self._mem:
                return self._mem.pop(0)
            return None

    def _worker_once(self) -> None:
        video_id: int | None = None
        try:
            raw = self._pop_payload()
            if not raw:
                return
            try:
                data = json.loads(raw)
                video_id = int(data["id"])
                enqueue_download = bool(data.get("enqueue"))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                logger.warning("invalid meta queue payload: {}", raw)
                return
            with self._active_lock:
                if video_id in self._active:
                    # 已在处理，丢回队列尾部避免丢任务
                    self.enqueue(video_id, enqueue_download=enqueue_download)
                    return
                self._active.add(video_id)
            self._fetch_one(video_id, enqueue_download=enqueue_download)
        except Exception as e:
            logger.exception("meta worker error: {}", e)
        finally:
            with self._active_lock:
                if video_id is not None:
                    self._active.discard(video_id)
                self._inflight = max(0, self._inflight - 1)
            # 没取到 payload 表示当前队列为空，worker 必须结束，不能自我递归 submit。
            if video_id is not None:
                self.kick()

    def _fetch_one(self, video_id: int, *, enqueue_download: bool) -> None:
        with db_session() as db:
            video = db.get(VideoModel, video_id)
            if video is None or video.delete_time is not None:
                return
            if video.status == META_OK and not enqueue_download:
                return
            url = video.url
            tenant_id = video.tenant_id

        logger.info("🔍 meta fetch start video_id={} url={}", video_id, url)
        try:
            info = extract_info(url)
            meta = normalize_meta(info, url)
            values: dict[str, Any] = {
                "title": meta.get("title"),
                "uploader": meta.get("uploader"),
                "description": meta.get("description"),
                "source": meta.get("source"),
                "best_resolution": meta.get("best_resolution"),
                "thumbnail": meta.get("thumbnail"),
                "duration": meta.get("duration"),
                "url": meta.get("url") or url,
                "info_json": meta.get("info_json"),
                "status": META_OK,
                "error_msg": None,
            }
        except Exception as e:
            logger.warning("meta fetch failed video_id={} err={}", video_id, e)
            values = {
                "status": META_FAIL,
                "error_msg": str(e)[:500],
            }
            if is_risk_control_error(e):
                values.update(
                    {
                        "title": None,
                        "uploader": None,
                        "description": None,
                        "source": None,
                        "best_resolution": None,
                        "thumbnail": None,
                        "duration": None,
                        "info_json": None,
                    }
                )

        job_id: int | None = None
        with db_session() as db:
            db.execute(update(VideoModel).where(VideoModel.id == video_id).values(**values))
            if enqueue_download and values.get("status") == META_OK:
                job = VideoDownloadModel(
                    video_id=video_id,
                    tenant_id=tenant_id,
                    mode="best",
                    options_json=None,
                    status=JOB_QUEUED,
                    progress=0.0,
                )
                db.add(job)
                db.flush()
                job_id = job.id
                db.execute(
                    update(VideoModel)
                    .where(VideoModel.id == video_id)
                    .values(active_job_id=job_id)
                )
            db.commit()

        logger.info(
            "✅ meta fetch done video_id={} status={} enqueue={}",
            video_id,
            values.get("status"),
            bool(job_id),
        )
        if job_id is not None:
            from .downloader import DownloadQueue

            DownloadQueue.instance().kick()
