"""yt-dlp in-process helpers. No app/settings imports — safe for the worker child."""

from __future__ import annotations

from typing import Any

_KEEP = (
    "id",
    "title",
    "uploader",
    "channel",
    "creator",
    "description",
    "extractor_key",
    "extractor",
    "ie_key",
    "webpage_url",
    "original_url",
    "thumbnail",
    "duration",
    "width",
    "height",
    "resolution",
    "_type",
)

_FMT_KEEP = (
    "format_id",
    "ext",
    "width",
    "height",
    "vcodec",
    "acodec",
    "filesize",
    "filesize_approx",
    "format_note",
    "format",
    "tbr",
    "resolution",
)


class _NullLogger:
    def debug(self, msg, *a, **k):
        pass

    def info(self, msg, *a, **k):
        pass

    def warning(self, msg, *a, **k):
        pass

    def error(self, msg, *a, **k):
        pass


def ydl_opts_base(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "logger": _NullLogger(),
    }
    if extra:
        opts.update(extra)
        cb = opts.get("cookiesfrombrowser")
        if isinstance(cb, list):
            opts["cookiesfrombrowser"] = tuple(cb)
    return opts


def slim_info(info: dict[str, Any], *, max_formats: int = 40, max_desc: int = 4000) -> dict[str, Any]:
    """Drop formats[].url / thumbnails / subs — those are the GB-scale dump."""
    out: dict[str, Any] = {}
    for k in _KEEP:
        v = info.get(k)
        if v is None:
            continue
        if k == "description" and isinstance(v, str) and len(v) > max_desc:
            v = v[:max_desc]
        out[k] = v
    fmts: list[dict[str, Any]] = []
    for f in (info.get("formats") or [])[:max_formats]:
        if not isinstance(f, dict):
            continue
        row = {k: f.get(k) for k in _FMT_KEEP if f.get(k) is not None}
        if row:
            fmts.append(row)
    if fmts:
        out["formats"] = fmts
    return out


def entry_webpage_url(entry: dict[str, Any]) -> str | None:
    for key in ("webpage_url", "original_url", "url"):
        val = entry.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val.strip()
    vid = entry.get("id")
    ie = str(entry.get("ie_key") or entry.get("extractor_key") or entry.get("extractor") or "").lower()
    if vid and ("youtube" in ie or (isinstance(vid, str) and len(vid) == 11)):
        return f"https://www.youtube.com/watch?v={vid}"
    if vid and "bilibili" in ie:
        return f"https://www.bilibili.com/video/{vid}"
    return None


def urls_from_flat_info(info: dict[str, Any], fallback_url: str) -> list[str]:
    if not isinstance(info, dict):
        return [fallback_url]
    entries = info.get("entries")
    if info.get("_type") == "playlist" or entries is not None:
        out: list[str] = []
        seen: set[str] = set()
        for e in entries or []:
            if not isinstance(e, dict):
                continue
            w = entry_webpage_url(e)
            if not w or w in seen:
                continue
            seen.add(w)
            out.append(w)
        if out:
            return out
        return [fallback_url]
    w = info.get("webpage_url") or info.get("original_url") or fallback_url
    return [str(w)]


def pick_best_resolution(info: dict[str, Any]) -> str | None:
    width = info.get("width")
    height = info.get("height")
    if width and height:
        return f"{width}x{height}"
    formats = info.get("formats") or []
    best_h = 0
    best = None
    for fmt in formats:
        h = fmt.get("height") or 0
        if h > best_h:
            best_h = h
            w = fmt.get("width")
            best = f"{w}x{h}" if w else f"{h}p"
    return best or info.get("resolution")


def pick_playable_url(info: dict[str, Any]) -> str | None:
    req = info.get("requested_formats") or []
    for f in req:
        if f.get("url") and f.get("vcodec") not in (None, "none"):
            return str(f["url"])
    if req and req[0].get("url"):
        return str(req[0]["url"])
    if info.get("url"):
        return str(info["url"])
    formats = [f for f in (info.get("formats") or []) if f.get("url")]
    video = [f for f in formats if f.get("vcodec") not in (None, "none")]
    pool = video or formats
    if not pool:
        return None
    pool.sort(key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
    return str(pool[0]["url"])


def extract_info_inproc(url: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_opts_base(extra)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp 返回空信息")
    return slim_info(info)


def expand_playlist_inproc(url: str, extra: dict[str, Any] | None = None) -> list[str]:
    import yt_dlp

    opts = {**ydl_opts_base(extra), "extract_flat": "in_playlist", "noplaylist": False}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        return [url]
    return urls_from_flat_info(info, url)


def list_formats_inproc(url: str, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_opts_base(extra)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        return []
    items: list[dict[str, Any]] = []
    for fmt in info.get("formats") or []:
        items.append(
            {
                "format_id": str(fmt.get("format_id", "")),
                "ext": fmt.get("ext"),
                "resolution": fmt.get("resolution")
                or (f"{fmt.get('width')}x{fmt.get('height')}" if fmt.get("height") else None),
                "vcodec": fmt.get("vcodec"),
                "acodec": fmt.get("acodec"),
                "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "note": fmt.get("format_note") or fmt.get("format"),
            }
        )
    return items


def list_video_qualities_inproc(url: str, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_opts_base(extra)) as ydl:
        info = ydl.extract_info(url, download=False, process=False)
    if not isinstance(info, dict):
        return []
    best_by_h: dict[int, dict[str, Any]] = {}
    for f in info.get("formats") or []:
        if f.get("vcodec") in (None, "none"):
            continue
        u = f.get("url")
        if not u:
            continue
        h = int(f.get("height") or 0)
        score = (
            1 if (f.get("ext") or "") in ("mp4", "m4v") else 0,
            1 if str(f.get("vcodec") or "").startswith(("avc", "h264")) else 0,
            float(f.get("tbr") or 0),
        )
        prev = best_by_h.get(h)
        if prev is not None and score <= prev["_score"]:
            continue
        label = f"{h}p" if h else str(f.get("format_note") or f.get("format_id") or "default")
        best_by_h[h] = {
            "label": label,
            "height": h or None,
            "url": str(u),
            "format_id": str(f.get("format_id") or ""),
            "_score": score,
        }
    items = sorted(best_by_h.values(), key=lambda x: x.get("height") or 0, reverse=True)
    for it in items:
        it.pop("_score", None)
    return items


def get_stream_url_inproc(url: str, format_id: str | None = None, extra: dict[str, Any] | None = None) -> str:
    import yt_dlp

    opts = ydl_opts_base(extra)
    opts["format"] = str(format_id) if format_id else "bestvideo"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        got = pick_playable_url(info if isinstance(info, dict) else {})
        if got:
            return got
    except Exception:
        if format_id:
            raise
    if format_id:
        raise RuntimeError(f"未找到 format_id={format_id} 的直链")
    quals = list_video_qualities_inproc(url, extra)
    if quals:
        return str(quals[0]["url"])
    raise RuntimeError("未找到 bestvideo 直链")


def compact_progress(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": d.get("status"),
        "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate"),
        "downloaded_bytes": d.get("downloaded_bytes"),
        "_percent": d.get("_percent"),
        "_speed_str": d.get("_speed_str"),
        "eta": d.get("eta"),
    }


def run_download_inproc(url: str, opts: dict[str, Any], progress_hook=None) -> None:
    import yt_dlp

    opts = {**opts, "logger": _NullLogger(), "quiet": True, "color": "never"}
    cb = opts.get("cookiesfrombrowser")
    if isinstance(cb, list):
        opts["cookiesfrombrowser"] = tuple(cb)
    if progress_hook:
        hooks = list(opts.get("progress_hooks") or [])
        hooks.append(progress_hook)
        opts = {**opts, "progress_hooks": hooks}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
