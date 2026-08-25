"""ponytail: yt-dlp 子进程协议 + slim 快照，不打真实网站。"""

import json

from app.api.v1.module_platform.video.downloader import DownloadQueue
from app.api.v1.module_platform.video.meta_queue import MetaFetchQueue
from app.api.v1.module_platform.video.ytdlp_core import slim_info
from app.api.v1.module_platform.video.ytdlp_util import _invoke_worker


class _FakeExecutor:
    def __init__(self) -> None:
        self.submitted = 0

    def submit(self, fn) -> None:
        self.submitted += 1


def test_worker_json_survives_gbk_pipe() -> None:
    """Windows 子进程 stdout=GBK 时，ensure_ascii JSON 仍能还原中文标题。"""
    payload = {"ok": True, "data": {"title": "测试标题", "uploader": "UP主"}}
    ascii_json = json.dumps(payload, ensure_ascii=True)
    recovered = json.loads(ascii_json.encode("gbk").decode("utf-8"))
    assert recovered["data"]["title"] == "测试标题"
    assert recovered["data"]["uploader"] == "UP主"
    # 对照：裸中文经 GBK→UTF-8 replace 会变成 �
    raw_cn = json.dumps(payload, ensure_ascii=False)
    broken = raw_cn.encode("gbk").decode("utf-8", errors="replace")
    assert "\ufffd" in broken


def test_slim_drops_direct_urls() -> None:
    fat = {
        "title": "hello",
        "formats": [{"format_id": "1", "url": "https://secret", "height": 1080}],
        "thumbnails": [{"url": "https://x"}] * 80,
    }
    slim = slim_info(fat)
    assert slim["title"] == "hello"
    assert slim["formats"][0]["height"] == 1080
    assert "url" not in slim["formats"][0]
    assert "thumbnails" not in slim


def test_worker_ping() -> None:
    assert _invoke_worker("ping", {}) == "pong"


def test_meta_queue_skips_recover_by_default() -> None:
    q = MetaFetchQueue()
    # 未 start 时 recover 仍可用；默认配置开关应为关
    from app.config.setting import settings

    assert settings.VIDEO_META_RECOVER_ON_START is False
    assert settings.VIDEO_YTDLP_SUBPROCESS is True
    q.stop()


def test_idle_video_workers_do_not_recursively_submit() -> None:
    """空队列 worker 退出时不能继续 kick，否则 Future 会无限堆积。"""
    dl = DownloadQueue()
    dl._started = True
    dl._executor = _FakeExecutor()  # type: ignore[assignment]
    dl.kick()
    initial_dl = dl._executor.submitted
    dl.kick()
    assert dl._executor.submitted == initial_dl
    dl._inflight = 1
    dl._claim_job = lambda: None  # type: ignore[method-assign]
    dl._worker_loop_once()
    assert dl._inflight == 0
    assert dl._executor.submitted == initial_dl

    meta = MetaFetchQueue()
    meta._started = True
    meta._executor = _FakeExecutor()  # type: ignore[assignment]
    meta.kick()
    initial_meta = meta._executor.submitted
    meta.kick()
    assert meta._executor.submitted == initial_meta
    meta._inflight = 1
    meta._pop_payload = lambda: None  # type: ignore[method-assign]
    meta._worker_once()
    assert meta._inflight == 0
    assert meta._executor.submitted == initial_meta


if __name__ == "__main__":
    test_slim_drops_direct_urls()
    test_worker_json_survives_gbk_pipe()
    test_worker_ping()
    test_meta_queue_skips_recover_by_default()
    test_idle_video_workers_do_not_recursively_submit()
    print("ok")
