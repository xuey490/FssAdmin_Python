"""yt-dlp 工具：元数据提取、直链、格式列表、路径清洗。

extract / download 默认丢给独立子进程，避免 info dump 留在 API 进程里。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from urllib.parse import urlparse

from app.core.logger import logger

from .ytdlp_core import (
    pick_best_resolution,
    slim_info,
)

_RISK_MARKERS = (
    "412",
    "precondition failed",
    "http error 412",
    "风控",
    "risk control",
    "access denied",
    "forbidden",
    "429",
    "too many requests",
)

_WORKER = Path(__file__).with_name("ytdlp_worker.py")
# ponytail: yt-dlp 子进程天花板；超时只保护 extract，下载走 Popen 无上限
_EXTRACT_TIMEOUT = 180


def is_x_url(url: str) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("mobile."):
        host = host[7:]
    return host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com")


def x_cookie_opts() -> dict[str, Any]:
    """仅 X 使用。cookie 文件优先；否则读本机浏览器。"""
    try:
        from app.config.path_conf import BASE_DIR
        from app.config.setting import settings
    except Exception:
        return {}

    cookie_file = str(getattr(settings, "VIDEO_X_COOKIES_FILE", "") or "").strip()
    if cookie_file:
        p = Path(cookie_file)
        if not p.is_absolute():
            p = BASE_DIR / p
        if p.is_file():
            return {"cookiefile": str(p)}
        logger.warning("VIDEO_X_COOKIES_FILE 不存在: {}", p)
        return {}

    browser = str(getattr(settings, "VIDEO_X_COOKIES_FROM_BROWSER", "chrome:Default") or "").strip()
    if not browser:
        return {}
    name, _, rest = browser.partition(":")
    name = name.strip()
    profile = rest.strip() or None
    if not name:
        return {}
    return {"cookiesfrombrowser": (name, profile) if profile else (name,)}


def ydl_extra_for_url(url: str) -> dict[str, Any]:
    return x_cookie_opts() if is_x_url(url) else {}


def is_risk_control_error(err: BaseException | str) -> bool:
    """判定是否为 412/风控类错误（应跳过并 status=-1）。"""
    text = str(err).lower()
    return any(m in text for m in _RISK_MARKERS)


def safe_title(title: str | None, fallback: str = "untitled", max_len: int = 80) -> str:
    """清洗标题为合法文件夹名：* # 等特殊字符统一替换为 -。"""
    raw = (title or "").strip() or fallback
    cleaned = re.sub(r'[<>:"/\\|?*#%&{}\x00-\x1f]', "-", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if not cleaned:
        cleaned = fallback
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(" .-")
    return cleaned


def video_output_dir(root: Path, title: str | None, video_id: int) -> Path:
    """同一视频复用目录；标题冲突时带短 hash。"""
    base = safe_title(title)
    suffix = hashlib.md5(f"{video_id}".encode()).hexdigest()[:6]
    return root / f"{base}_{suffix}"


def _use_subprocess() -> bool:
    try:
        from app.config.setting import settings

        return bool(getattr(settings, "VIDEO_YTDLP_SUBPROCESS", True))
    except Exception:
        return True


def _popen_kwargs() -> dict[str, Any]:
    kw: dict[str, Any] = {}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return kw


def _worker_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _dumps_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def _invoke_worker(cmd: str, payload: dict[str, Any], *, timeout: float | None = _EXTRACT_TIMEOUT) -> Any:
    if not _use_subprocess():
        from . import ytdlp_core as core

        if cmd == "ping":
            return "pong"
        if cmd == "extract":
            return core.extract_info_inproc(str(payload["url"]), payload.get("opts"))
        if cmd == "expand":
            return core.expand_playlist_inproc(str(payload["url"]), payload.get("opts"))
        if cmd == "formats":
            return core.list_formats_inproc(str(payload["url"]), payload.get("opts"))
        if cmd == "qualities":
            return core.list_video_qualities_inproc(str(payload["url"]), payload.get("opts"))
        if cmd == "stream":
            fmt = payload.get("format_id")
            return core.get_stream_url_inproc(str(payload["url"]), str(fmt) if fmt else None, payload.get("opts"))
        raise ValueError(f"unknown cmd={cmd}")

    proc = subprocess.run(
        [sys.executable, str(_WORKER), cmd],
        input=_dumps_payload(payload),
        capture_output=True,
        timeout=timeout,
        env=_worker_env(),
        **_popen_kwargs(),
    )
    raw = (proc.stdout or b"").decode("utf-8").strip()
    if not raw:
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip() or f"yt-dlp worker exit {proc.returncode}"
        raise RuntimeError(err[:500])
    try:
        body = json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"yt-dlp worker bad json: {raw[:200]}") from e
    if not body.get("ok"):
        raise RuntimeError(str(body.get("msg") or "yt-dlp failed")[:500])
    return body.get("data")


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def _payload_with_url(url: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"url": url}
    opts = extra if extra is not None else ydl_extra_for_url(url)
    if opts:
        payload["opts"] = opts
    return payload


def expand_playlist_urls(url: str) -> list[str]:
    """等价 ``yt-dlp -s --flat-playlist --dump-single-json``，再抽出 webpage_url 列表。"""
    got = _invoke_worker("expand", _payload_with_url(url))
    if isinstance(got, list) and got:
        return [str(x) for x in got if x]
    return [url]


def resolve_input_urls(urls: list[str]) -> list[str]:
    """入库前对每条链接做 flat 解析：合集/多 P 展开，单集取 webpage_url；去重保序。"""
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls:
        u = (raw or "").strip()
        if not u:
            continue
        try:
            parts = expand_playlist_urls(u)
            if len(parts) > 1:
                logger.info("multi entry expanded src={} -> {} urls", u, len(parts))
            elif parts and parts[0] != u:
                logger.info("normalized webpage_url src={} -> {}", u, parts[0])
        except Exception as e:
            logger.warning("flat resolve failed src={} err={}", u, e)
            parts = [u]
        for p in parts:
            p = (p or "").strip()
            if not p or p in seen:
                continue
            seen.add(p)
            out.append(p)
    return out


def extract_info(url: str) -> dict[str, Any]:
    """等价 yt-dlp -s -j，返回瘦身 info（无 formats[].url）。"""
    info = _invoke_worker("extract", _payload_with_url(url))
    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp 返回空信息")
    return info


def normalize_meta(info: dict[str, Any], fallback_url: str) -> dict[str, Any]:
    """从 dump-json 提取入库字段。info_json 只存 slim 快照。"""
    slim = slim_info(info) if info else {}
    return {
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel") or info.get("creator"),
        "description": info.get("description"),
        "source": info.get("extractor_key") or info.get("extractor") or info.get("ie_key"),
        "best_resolution": pick_best_resolution(info),
        "thumbnail": info.get("thumbnail"),
        "duration": int(info.get("duration") or 0) or None,
        "url": info.get("webpage_url") or fallback_url,
        "info_json": slim,
    }


def list_formats(url: str) -> list[dict[str, Any]]:
    got = _invoke_worker("formats", _payload_with_url(url))
    return got if isinstance(got, list) else []


def list_video_qualities(url: str) -> list[dict[str, Any]]:
    """列出各清晰度视频轨直链（仅画面，不含音频），按 height 降序去重。"""
    got = _invoke_worker("qualities", _payload_with_url(url))
    return got if isinstance(got, list) else []


def get_bestvideo_url(url: str) -> str:
    """等价 ``yt-dlp -s -f bestvideo -g``：只取最高清视频轨直链。"""
    got = _invoke_worker("stream", _payload_with_url(url))
    if not got:
        raise RuntimeError("未找到 bestvideo 直链")
    return str(got)


def get_format_stream_url(url: str, format_id: str) -> str:
    """按 format_id 取直链（供代理流切换清晰度）。"""
    got = _invoke_worker("stream", {**_payload_with_url(url), "format_id": str(format_id)})
    if not got:
        raise RuntimeError(f"未找到 format_id={format_id} 的直链")
    return str(got)


def get_best_stream_url(url: str) -> str:
    """预览/代理用：默认走 bestvideo。"""
    return get_bestvideo_url(url)


def build_download_opts(
    *,
    outtmpl: str,
    mode: str,
    options: dict[str, Any] | None,
    continuedl: bool = True,
    url: str | None = None,
) -> dict[str, Any]:
    options = options or {}
    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "no_warnings": True,
        "continuedl": continuedl,
        "noprogress": True,
        "retries": 3,
        "color": "never",
    }
    if mode == "best":
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
        opts["writethumbnail"] = True
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = ["all", "-live_chat", "-danmaku"]
        opts["ignoreerrors"] = "only_download"
    elif mode == "custom":
        fmt = options.get("format_id")
        audio = options.get("audio_format")
        height = options.get("height")
        if fmt and audio:
            opts["format"] = f"{fmt}+{audio}"
            opts["merge_output_format"] = "mp4"
        elif fmt:
            opts["format"] = str(fmt)
        elif height:
            opts["format"] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"
        opts["writethumbnail"] = True
        if options.get("sub_langs"):
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = [s.strip() for s in str(options["sub_langs"]).split(",") if s.strip()]
            opts["ignoreerrors"] = "only_download"
    elif mode == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.get("audio_format") or "mp3",
                "preferredquality": "192",
            }
        ]
    elif mode == "subs":
        opts["skip_download"] = True
        opts["writethumbnail"] = True
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        langs = [s.strip() for s in str(options.get("sub_langs") or "all").split(",") if s.strip()] or ["all"]
        if "all" in langs:
            langs = [*langs, "-live_chat", "-danmaku"]
        opts["subtitleslangs"] = langs
        opts["ignoreerrors"] = "only_download"
    else:
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
    extra = ydl_extra_for_url(url) if url else {}
    if extra:
        opts.update(extra)
    return opts


def _jsonable_opts(opts: dict[str, Any]) -> dict[str, Any]:
    skip = {"progress_hooks", "logger"}
    return {k: v for k, v in opts.items() if k not in skip}


def run_download(url: str, opts: dict[str, Any], progress_hook=None) -> None:
    if not _use_subprocess():
        from .ytdlp_core import run_download_inproc

        logger.info("yt-dlp download start url={}", url)
        run_download_inproc(url, opts, progress_hook=progress_hook)
        logger.info("yt-dlp download done url={}", url)
        return

    logger.info("yt-dlp download start url={}", url)
    proc = subprocess.Popen(
        [sys.executable, str(_WORKER), "download"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=_worker_env(),
        **_popen_kwargs(),
    )
    assert proc.stdin and proc.stdout
    try:
        proc.stdin.write(_dumps_payload({"url": url, "opts": _jsonable_opts(opts)}))
        proc.stdin.close()
        for raw_line in proc.stdout:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = msg.get("t")
            if kind == "p" and progress_hook:
                progress_hook(msg.get("d") or {})
            elif kind == "err":
                raise RuntimeError(str(msg.get("msg") or "download failed")[:500])
            elif kind == "ok":
                break
    except BaseException:
        _kill(proc)
        raise
    rc = proc.wait(timeout=10)
    if rc != 0:
        raise RuntimeError(f"yt-dlp worker exit {rc}")
    logger.info("yt-dlp download done url={}", url)
