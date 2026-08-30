"""ponytail: 视频模块最小自检（无网络）— 标题清洗 / 412 判定 / 队列状态机。"""

from __future__ import annotations

from app.api.v1.module_platform.video.constants import (
    JOB_DONE,
    JOB_FAILED,
    JOB_PAUSED,
    JOB_QUEUED,
    JOB_RUNNING,
    JOB_STOPPED,
    can_transition,
)
from app.api.v1.module_platform.video.ytdlp_core import (
    entry_webpage_url as _entry_webpage_url,
    pick_playable_url as _pick_playable_url,
    slim_info,
    urls_from_flat_info,
)
from app.api.v1.module_platform.video.ytdlp_util import (
    is_risk_control_error,
    is_x_url,
    normalize_meta,
    safe_title,
    ydl_extra_for_url,
)


def _check_title_json_pipe() -> None:
    import json

    payload = {"title": "【标题】测试"}
    ascii_json = json.dumps(payload, ensure_ascii=True)
    assert json.loads(ascii_json.encode("gbk").decode("utf-8"))["title"] == "【标题】测试"


def _check_safe_title() -> None:
    assert safe_title('a/b:c*?') == 'a-b-c'
    assert safe_title('#64cb010【标题】') == '64cb010【标题】'
    assert safe_title('a#b*c') == 'a-b-c'
    assert safe_title('') == 'untitled'
    assert len(safe_title('x' * 200)) <= 80


def _check_pick_url() -> None:
    # B 站风格：分离流，应取画面轨
    assert (
        _pick_playable_url(
            {
                "requested_formats": [
                    {"url": "https://a/v", "vcodec": "avc1", "acodec": "none"},
                    {"url": "https://a/a", "vcodec": "none", "acodec": "mp4a"},
                ]
            }
        )
        == "https://a/v"
    )
    # 无 requested_formats 时从 formats 挑最高
    assert (
        _pick_playable_url(
            {
                "formats": [
                    {"url": "https://low", "vcodec": "avc1", "height": 360},
                    {"url": "https://hi", "vcodec": "avc1", "height": 1080},
                ]
            }
        )
        == "https://hi"
    )


def _check_quality_dedupe() -> None:
    # ponytail: list_video_qualities 依赖网络；这里只验同高度打分挑选逻辑的等价排序
    rows = [
        {"url": "https://flv", "vcodec": "avc1", "ext": "flv", "height": 720, "tbr": 2000},
        {"url": "https://mp4", "vcodec": "avc1", "ext": "mp4", "height": 720, "tbr": 1500},
        {"url": "https://1080", "vcodec": "avc1", "ext": "mp4", "height": 1080, "tbr": 3000},
    ]
    best_by_h: dict[int, dict] = {}
    for f in rows:
        h = int(f["height"])
        score = (
            1 if f["ext"] in ("mp4", "m4v") else 0,
            1 if str(f["vcodec"]).startswith(("avc", "h264")) else 0,
            float(f["tbr"]),
        )
        prev = best_by_h.get(h)
        if prev is None or score > prev["_score"]:
            best_by_h[h] = {**f, "_score": score}
    assert best_by_h[720]["url"] == "https://mp4"
    assert sorted(best_by_h, reverse=True)[0] == 1080


def _check_playlist_detect() -> None:
    # B 站多 P：看起来像单链，但 dump-json 是 playlist
    bili_multi = {
        "_type": "playlist",
        "id": "BV1AxsmeZEem",
        "entries": [
            {"ie_key": "BiliBili", "_type": "url", "url": f"https://www.bilibili.com/video/BV1AxsmeZEem?p={i}"}
            for i in range(1, 4)
        ],
    }
    got = urls_from_flat_info(bili_multi, "https://www.bilibili.com/video/BV1AxsmeZEem")
    assert got == [
        "https://www.bilibili.com/video/BV1AxsmeZEem?p=1",
        "https://www.bilibili.com/video/BV1AxsmeZEem?p=2",
        "https://www.bilibili.com/video/BV1AxsmeZEem?p=3",
    ]
    # 真正单集
    single = {
        "_type": "video",
        "webpage_url": "https://www.youtube.com/watch?v=OTigkbqe3wU",
    }
    assert urls_from_flat_info(single, "https://youtu.be/OTigkbqe3wU") == [
        "https://www.youtube.com/watch?v=OTigkbqe3wU"
    ]
    assert (
        _entry_webpage_url({"id": "OTigkbqe3wU", "ie_key": "Youtube"})
        == "https://www.youtube.com/watch?v=OTigkbqe3wU"
    )


def _check_slim_info() -> None:
    fat = {
        "title": "t",
        "description": "d" * 5000,
        "thumbnail": "https://img/ok",
        "thumbnails": [{"url": f"https://img/{i}"} for i in range(200)],
        "subtitles": {"en": [{"url": "https://huge"}]},
        "formats": [
            {
                "format_id": "22",
                "ext": "mp4",
                "height": 720,
                "url": "https://direct.example/secret",
                "http_headers": {"Cookie": "x" * 1000},
                "fragments": [{"url": "https://frag"}] * 50,
            }
        ],
    }
    slim = slim_info(fat)
    assert slim["title"] == "t"
    assert slim["thumbnail"] == "https://img/ok"
    assert "thumbnails" not in slim
    assert "subtitles" not in slim
    assert "url" not in slim["formats"][0]
    assert "http_headers" not in slim["formats"][0]
    assert "fragments" not in slim["formats"][0]
    assert slim["formats"][0]["format_id"] == "22"
    assert len(slim["description"]) == 4000
    meta = normalize_meta(fat, "https://fallback")
    assert meta["info_json"]["title"] == "t"
    assert "url" not in (meta["info_json"].get("formats") or [{}])[0]


def _check_risk() -> None:
    assert is_risk_control_error('HTTP Error 412: Precondition Failed')
    assert is_risk_control_error('风控校验失败')
    assert not is_risk_control_error('Video unavailable')


def _check_transitions() -> None:
    assert can_transition(JOB_QUEUED, JOB_RUNNING)
    assert can_transition(JOB_RUNNING, JOB_PAUSED)
    assert can_transition(JOB_RUNNING, JOB_STOPPED)
    assert can_transition(JOB_RUNNING, JOB_DONE)
    assert can_transition(JOB_PAUSED, JOB_QUEUED)
    assert can_transition(JOB_FAILED, JOB_QUEUED)
    assert not can_transition(JOB_DONE, JOB_RUNNING)
    assert not can_transition(JOB_QUEUED, JOB_DONE)


def _check_x_url() -> None:
    assert is_x_url("https://x.com/a/status/1")
    assert is_x_url("https://www.x.com/a/status/1")
    assert is_x_url("https://twitter.com/a/status/1")
    assert is_x_url("https://mobile.twitter.com/a/status/1")
    assert not is_x_url("https://youtube.com/watch?v=1")
    assert ydl_extra_for_url("https://youtube.com/watch?v=1") == {}


def main() -> None:
    _check_title_json_pipe()
    _check_safe_title()
    _check_pick_url()
    _check_quality_dedupe()
    _check_playlist_detect()
    _check_slim_info()
    _check_risk()
    _check_transitions()
    _check_x_url()
    print('video_self_check ok')


if __name__ == '__main__':
    main()
