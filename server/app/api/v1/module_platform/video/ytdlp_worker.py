"""yt-dlp child process. Run as a file (not -m app...) so the API process stays small.

Protocol:
  argv[1] = command
  stdin  = JSON payload
  stdout = one JSON object (extract/expand/...) or JSONL for download
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# script dir first so `import ytdlp_core` works when launched by path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _force_utf8_stdio() -> None:
    """Windows 默认管道编码是 GBK；中文 title 会被父进程 utf-8/replace 读成 �。"""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if reconf is None:
            continue
        try:
            reconf(encoding="utf-8", errors="strict", newline="\n")
        except Exception:
            pass


def _out(obj: dict) -> None:
    # ponytail: ensure_ascii 让 JSON 全是 ASCII，管道无论 GBK/UTF-8 都不会把标题打成 �
    line = json.dumps(obj, ensure_ascii=True) + "\n"
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        buf.write(line.encode("utf-8"))
        buf.flush()
        return
    sys.stdout.write(line)
    sys.stdout.flush()


def _dispatch(cmd: str, payload: dict) -> object:
    from ytdlp_core import (
        expand_playlist_inproc,
        extract_info_inproc,
        get_stream_url_inproc,
        list_formats_inproc,
        list_video_qualities_inproc,
    )

    url = str(payload.get("url") or "")
    if cmd == "extract":
        return extract_info_inproc(url)
    if cmd == "expand":
        return expand_playlist_inproc(url)
    if cmd == "formats":
        return list_formats_inproc(url)
    if cmd == "qualities":
        return list_video_qualities_inproc(url)
    if cmd == "stream":
        fmt = payload.get("format_id")
        return get_stream_url_inproc(url, str(fmt) if fmt else None)
    raise ValueError(f"unknown cmd={cmd}")


def _download(payload: dict) -> None:
    from ytdlp_core import compact_progress, run_download_inproc

    url = str(payload.get("url") or "")
    opts = dict(payload.get("opts") or {})

    def hook(d: dict) -> None:
        st = d.get("status")
        if st in ("downloading", "finished"):
            _out({"t": "p", "d": compact_progress(d)})

    run_download_inproc(url, opts, progress_hook=hook)
    _out({"t": "ok"})


def main() -> int:
    _force_utf8_stdio()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        raw_in = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read()
        if isinstance(raw_in, bytes):
            payload = json.loads(raw_in.decode("utf-8") or "{}")
        else:
            payload = json.loads(raw_in or "{}")
    except json.JSONDecodeError as e:
        _out({"ok": False, "msg": f"bad stdin json: {e}"})
        return 1
    if cmd == "ping":
        _out({"ok": True, "data": "pong"})
        return 0
    if cmd == "download":
        try:
            _download(payload if isinstance(payload, dict) else {})
            return 0
        except Exception as e:
            _out({"t": "err", "msg": str(e)})
            return 1
    try:
        data = _dispatch(cmd, payload if isinstance(payload, dict) else {})
        _out({"ok": True, "data": data})
        return 0
    except Exception as e:
        _out({"ok": False, "msg": str(e)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
