"""ponytail: redis browser 二进制值预览。"""

from __future__ import annotations

from app.api.v1.module_monitor.core_server import _binary_preview, _format_redis_scalar


def main() -> None:
    raw = b"\x80\x04\x95"  # pickle 协议头
    prev = _binary_preview(raw)
    assert prev["_binary"] is True and prev["size"] == 3
    assert _format_redis_scalar(b"hello") == "hello"
    assert _format_redis_scalar(raw)["_binary"] is True
    print("ok: redis binary preview")


if __name__ == "__main__":
    main()
