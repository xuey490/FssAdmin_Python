"""下载队列：DB 认领 + Redis 控制/热进度 + 线程池工人。"""

from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from app.config.setting import settings
from app.core.database import db_session
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
    REDIS_CTRL_PREFIX,
    REDIS_PROGRESS_PREFIX,
)
from .model import VideoDownloadModel, VideoModel
from .ytdlp_util import build_download_opts, run_download, safe_title, video_output_dir


class DownloadAbort(Exception):
    """用户暂停/停止触发的中断。"""

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(action)


class DownloadQueue:
    """进程内单例下载队列。"""

    _instance: DownloadQueue | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._active: set[int] = set()
        self._active_lock = threading.Lock()
        # _inflight 包含已经 submit 但尚未开始认领任务的 worker，防止空队列时递归 submit。
        self._inflight = 0
        self._redis = None
        self._started = False
        self._stop_event = threading.Event()

    @classmethod
    def instance(cls) -> DownloadQueue:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        if not settings.REDIS_ENABLE:
            return None
        try:
            import redis

            auth_kwargs: dict[str, Any] = {}
            if settings.REDIS_PASSWORD:
                auth_kwargs["password"] = settings.REDIS_PASSWORD
            if settings.REDIS_USER:
                auth_kwargs["username"] = settings.REDIS_USER
            self._redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=int(settings.REDIS_DB_NAME),
                decode_responses=True,
                **auth_kwargs,
            )
            self._redis.ping()
            return self._redis
        except Exception as e:
            logger.warning("video download sync redis unavailable: {}", e)
            self._redis = False  # type: ignore[assignment]
            return None

    def set_ctrl(self, job_id: int, ctrl: str) -> None:
        rd = self._get_redis()
        if rd:
            rd.set(f"{REDIS_CTRL_PREFIX}{job_id}", ctrl, ex=86400)

    def get_ctrl(self, job_id: int) -> str:
        if self._stop_event.is_set():
            return CTRL_STOP
        rd = self._get_redis()
        if rd:
            val = rd.get(f"{REDIS_CTRL_PREFIX}{job_id}")
            if val:
                return str(val)
        # 降级：读 DB status
        with db_session() as db:
            row = db.get(VideoDownloadModel, job_id)
            if row is None:
                return CTRL_RUN
            if row.status == JOB_PAUSED:
                return CTRL_PAUSE
            if row.status == JOB_STOPPED:
                return CTRL_STOP
            return CTRL_RUN

    def set_progress_cache(self, job_id: int, payload: dict[str, Any]) -> None:
        rd = self._get_redis()
        if rd:
            rd.set(f"{REDIS_PROGRESS_PREFIX}{job_id}", json.dumps(payload), ex=3600)

    def get_progress_cache(self, job_id: int) -> dict[str, Any] | None:
        rd = self._get_redis()
        if not rd:
            return None
        raw = rd.get(f"{REDIS_PROGRESS_PREFIX}{job_id}")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def start(self) -> None:
        if self._started:
            return
        self._stop_event.clear()
        workers = max(1, int(settings.VIDEO_DOWNLOAD_WORKERS or 2))
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="video-dl")
        self._started = True
        recovered = self.recover_crashed()
        logger.info("DownloadQueue started workers={} recovered={}", workers, recovered)
        self.kick()

    def stop(self, *, reason: str = "服务关闭") -> None:
        """停止队列：向进行中任务发 CTRL_STOP，打断 yt-dlp，再关掉线程池。"""
        if not self._started and self._executor is None:
            return
        logger.info("DownloadQueue stopping: {}", reason)
        self._stop_event.set()
        self._started = False
        with self._active_lock:
            active_ids = list(self._active)
        for job_id in active_ids:
            try:
                self.set_ctrl(job_id, CTRL_STOP)
            except Exception as e:
                logger.warning("set_ctrl stop failed job={}: {}", job_id, e)
        try:
            with db_session() as db:
                rows = db.execute(
                    select(VideoDownloadModel.id).where(
                        VideoDownloadModel.status == JOB_RUNNING,
                        VideoDownloadModel.delete_time.is_(None),
                    )
                ).scalars().all()
                for jid in rows:
                    self.set_ctrl(int(jid), CTRL_STOP)
        except Exception as e:
            logger.warning("DownloadQueue stop signal running failed: {}", e)
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
        with self._active_lock:
            self._inflight = 0
        deadline = time.time() + 3.0
        while time.time() < deadline:
            with self._active_lock:
                if not self._active:
                    break
            time.sleep(0.15)
        with self._active_lock:
            left = list(self._active)
        if left:
            logger.warning("DownloadQueue stop: still active jobs={} (next start will requeue)", left)
        logger.info("DownloadQueue stopped")

    def recover_crashed(self) -> int:
        """running → queued（进程崩溃恢复）；paused 保持。"""
        with db_session() as db:
            result = db.execute(
                update(VideoDownloadModel)
                .where(VideoDownloadModel.status == JOB_RUNNING)
                .where(VideoDownloadModel.delete_time.is_(None))
                .values(status=JOB_QUEUED, error_msg="进程重启，任务重新入队")
            )
            db.commit()
            return int(result.rowcount or 0)

    def kick(self) -> None:
        if not self._started or not self._executor or self._stop_event.is_set():
            return
        workers = max(1, int(settings.VIDEO_DOWNLOAD_WORKERS or 2))
        with self._active_lock:
            slots = max(0, workers - self._inflight)
            self._inflight += slots
        for _ in range(max(0, slots)):
            try:
                self._executor.submit(self._worker_loop_once)
            except Exception:
                with self._active_lock:
                    self._inflight -= 1
                raise

    def _claim_job(self) -> int | None:
        if self._stop_event.is_set() or not self._started:
            return None
        with db_session() as db:
            q = (
                select(VideoDownloadModel)
                .where(VideoDownloadModel.status == JOB_QUEUED)
                .where(VideoDownloadModel.delete_time.is_(None))
                .order_by(VideoDownloadModel.priority.desc(), VideoDownloadModel.id.asc())
                .limit(1)
            )
            try:
                q = q.with_for_update(skip_locked=True)
                row = db.execute(q).scalar_one_or_none()
            except Exception:
                # sqlite 等不支持 skip_locked
                row = db.execute(
                    select(VideoDownloadModel)
                    .where(VideoDownloadModel.status == JOB_QUEUED)
                    .where(VideoDownloadModel.delete_time.is_(None))
                    .order_by(VideoDownloadModel.priority.desc(), VideoDownloadModel.id.asc())
                    .limit(1)
                ).scalar_one_or_none()
            if row is None:
                return None
            job_id = row.id
            row.status = JOB_RUNNING
            row.started_at = datetime.now()
            row.error_msg = None
            video = db.get(VideoModel, row.video_id)
            if video:
                video.active_job_id = job_id
            db.commit()
            self.set_ctrl(job_id, CTRL_RUN)
            return job_id

    def _worker_loop_once(self) -> None:
        if self._stop_event.is_set() or not self._started:
            return
        job_id = None
        try:
            job_id = self._claim_job()
            if job_id is None:
                return
            with self._active_lock:
                self._active.add(job_id)
            self._run_job(job_id)
        except Exception as e:
            logger.exception("download worker error: {}", e)
            if job_id is not None:
                self._finish_job(job_id, JOB_FAILED, str(e)[:500])
        finally:
            with self._active_lock:
                if job_id is not None:
                    self._active.discard(job_id)
                self._inflight = max(0, self._inflight - 1)
            # 只有真正消费过任务才继续拉下一项；空队列 worker 到此停止。
            if job_id is not None:
                self.kick()

    def _run_job(self, job_id: int) -> None:
        with db_session() as db:
            job = db.get(VideoDownloadModel, job_id)
            if job is None:
                return
            video = db.get(VideoModel, job.video_id)
            if video is None:
                self._finish_job(job_id, JOB_FAILED, "视频不存在")
                return
            url = video.url
            mode = job.mode
            options = job.options_json or {}
            title = video.title
            video_id = video.id
            # 续传：非首次则 continuedl
            continuedl = True

        root = Path(settings.VIDEO_DOWNLOAD_ROOT)
        if not root.is_absolute():
            from app.config.path_conf import BASE_DIR

            root = BASE_DIR / root
        out_dir = video_output_dir(root, title, video_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        # 文件名与目录同一套清洗，避免 * # 等进磁盘名
        outtmpl = str(out_dir / f"{safe_title(title)}.%(ext)s")

        with db_session() as db:
            job = db.get(VideoDownloadModel, job_id)
            if job:
                job.local_dir = str(out_dir)
                db.commit()

        opts = build_download_opts(outtmpl=outtmpl, mode=mode, options=options, continuedl=continuedl)
        last_flush = 0.0
        state: dict[str, Any] = {"progress": 0.0, "downloaded_bytes": 0, "total_bytes": None, "speed": None, "eta": None}

        def hook(d: dict[str, Any]) -> None:
            nonlocal last_flush
            from yt_dlp.utils import DownloadCancelled

            # 服务关闭 / 全局停止：尽快打断，避免主进程退出后线程还在下
            if self._stop_event.is_set():
                raise DownloadCancelled("shutdown")
            ctrl = self.get_ctrl(job_id)
            # DownloadCancelled 不会被 ignoreerrors 吞掉，避免暂停被当成下载成功 → 进度 100%
            if ctrl == CTRL_PAUSE:
                raise DownloadCancelled("pause")
            if ctrl == CTRL_STOP:
                raise DownloadCancelled("stop")
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = int(d.get("downloaded_bytes") or 0)
                # 禁止解析 _percent_str：终端开启颜色时含 ANSI（\x1b[0;94m 0.0\x1b[0m）
                pct = 0.0
                if total:
                    pct = round(downloaded * 100.0 / float(total), 2)
                else:
                    raw_pct = d.get("_percent")
                    if isinstance(raw_pct, (int, float)):
                        pct = float(raw_pct)
                speed = d.get("_speed_str")
                if isinstance(speed, str):
                    speed = re.sub(r"\x1b\[[0-9;]*m", "", speed).strip() or None
                eta = d.get("eta")
                state.update(
                    {
                        "progress": min(pct, 99.9),
                        "downloaded_bytes": downloaded,
                        "total_bytes": int(total) if total else None,
                        "speed": speed,
                        "eta": int(eta) if isinstance(eta, (int, float)) else None,
                    }
                )
                self.set_progress_cache(job_id, state)
                now = time.time()
                if now - last_flush >= 1.5:
                    last_flush = now
                    self._flush_progress(job_id, state)
                    bar_len = 20
                    filled = int(bar_len * min(state["progress"], 100) / 100)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    logger.info(
                        "⬇️ job={} |{}| {:>5.1f}%  {}  eta={}",
                        job_id,
                        bar,
                        state["progress"],
                        speed or "-",
                        eta if eta is not None else "-",
                    )
            elif d.get("status") == "finished":
                # 字幕/缩略图等附属文件 finished 时不要把进度直接打满，留给主视频
                if d.get("total_bytes") or d.get("downloaded_bytes"):
                    state["progress"] = max(float(state.get("progress") or 0), 99.0)
                self.set_progress_cache(job_id, state)
                self._flush_progress(job_id, state)

        try:
            run_download(url, opts, progress_hook=hook)
            # ignoreerrors 等极端情况：即使未抛错也再读 ctrl，避免误标完成
            if self._stop_event.is_set():
                self._finish_job(job_id, JOB_STOPPED, "服务关闭", local_dir=str(out_dir))
            else:
                ctrl = self.get_ctrl(job_id)
                if ctrl == CTRL_PAUSE:
                    self._finish_job(job_id, JOB_PAUSED, "用户暂停", local_dir=str(out_dir))
                elif ctrl == CTRL_STOP:
                    self._finish_job(job_id, JOB_STOPPED, "用户停止", local_dir=str(out_dir))
                else:
                    self._finish_job(job_id, JOB_DONE, None, local_dir=str(out_dir), video_id=video_id)
        except DownloadAbort as e:
            if e.action == CTRL_PAUSE:
                self._finish_job(job_id, JOB_PAUSED, "用户暂停", local_dir=str(out_dir))
            else:
                self._finish_job(job_id, JOB_STOPPED, "用户停止", local_dir=str(out_dir))
        except Exception as e:
            from yt_dlp.utils import DownloadCancelled

            ctrl = self.get_ctrl(job_id)
            msg = str(e).lower()
            is_cancel = isinstance(e, DownloadCancelled) or "cancel" in msg
            if self._stop_event.is_set() or (is_cancel and "shutdown" in msg):
                self._finish_job(job_id, JOB_STOPPED, "服务关闭", local_dir=str(out_dir))
            elif ctrl == CTRL_PAUSE or (is_cancel and "pause" in msg):
                self._finish_job(job_id, JOB_PAUSED, "用户暂停", local_dir=str(out_dir))
            elif ctrl == CTRL_STOP or (is_cancel and "stop" in msg):
                self._finish_job(job_id, JOB_STOPPED, "用户停止", local_dir=str(out_dir))
            elif is_cancel:
                # DownloadCancelled 但 ctrl 已被改回 run：按暂停收尾，避免误标 100%
                self._finish_job(job_id, JOB_PAUSED, "用户暂停", local_dir=str(out_dir))
            else:
                logger.exception("job {} download failed: {}", job_id, e)
                self._finish_job(job_id, JOB_FAILED, str(e)[:500], local_dir=str(out_dir))

    def _flush_progress(self, job_id: int, state: dict[str, Any]) -> None:
        with db_session() as db:
            db.execute(
                update(VideoDownloadModel)
                .where(VideoDownloadModel.id == job_id)
                .values(
                    progress=state.get("progress") or 0,
                    downloaded_bytes=state.get("downloaded_bytes") or 0,
                    total_bytes=state.get("total_bytes"),
                    speed=state.get("speed"),
                    eta=state.get("eta"),
                )
            )
            db.commit()

    def _finish_job(
        self,
        job_id: int,
        status: int,
        error_msg: str | None,
        *,
        local_dir: str | None = None,
        video_id: int | None = None,
    ) -> None:
        with db_session() as db:
            job = db.get(VideoDownloadModel, job_id)
            if job is None:
                return
            job.status = status
            job.error_msg = error_msg
            job.finished_at = datetime.now() if status in (JOB_DONE, JOB_FAILED, JOB_STOPPED) else None
            if status == JOB_DONE:
                job.progress = 100.0
            elif status in (JOB_PAUSED, JOB_STOPPED):
                # 保留暂停前真实进度，禁止写成 100%
                cache = self.get_progress_cache(job_id)
                if cache and "progress" in cache:
                    job.progress = float(cache["progress"])
                    if cache.get("downloaded_bytes") is not None:
                        job.downloaded_bytes = int(cache["downloaded_bytes"] or 0)
                    if cache.get("total_bytes") is not None:
                        job.total_bytes = cache.get("total_bytes")
                    job.speed = None
            if local_dir:
                job.local_dir = local_dir
            vid = video_id or job.video_id
            video = db.get(VideoModel, vid)
            if video:
                if status == JOB_DONE and local_dir:
                    video.local_dir = local_dir
                if status in (JOB_DONE, JOB_FAILED, JOB_STOPPED):
                    if video.active_job_id == job_id:
                        video.active_job_id = None
                elif status == JOB_PAUSED:
                    video.active_job_id = job_id
            progress_log = float(job.progress or 0)
            db.commit()
        logger.info("job {} finished status={} progress={}", job_id, status, progress_log)
