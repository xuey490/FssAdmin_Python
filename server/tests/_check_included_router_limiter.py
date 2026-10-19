"""ponytail: 限流不扫 route.path，避免 FastAPI 0.137+ 的 _IncludedRouter 炸。"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENVIRONMENT", "dev")

from starlette.requests import Request
from starlette.responses import Response

from app.core import http_limit
from app.core.http_limit import RateLimiter


async def _run() -> None:
    redis = SimpleNamespace(incr=AsyncMock(return_value=1), expire=AsyncMock(), ttl=AsyncMock(return_value=60))
    await http_limit.init_limiter(redis=redis, prefix="t:")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/core/captcha",
        "raw_path": b"/core/captcha",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1),
        "server": ("127.0.0.1", 80),
        "app": SimpleNamespace(routes=[SimpleNamespace()]),  # no .path
    }
    await RateLimiter(times=1, seconds=60)(Request(scope), Response())
    redis.incr.assert_awaited()
    await http_limit.close_limiter()
    print("ok: limiter ignores routes without .path")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
