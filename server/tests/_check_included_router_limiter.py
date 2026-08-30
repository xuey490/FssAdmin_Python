"""ponytail: fastapi-limiter 扫 route.path 会在 FastAPI 0.137+ 的 _IncludedRouter 上炸。"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENVIRONMENT", "dev")

from fastapi_limiter import FastAPILimiter
from starlette.requests import Request
from starlette.responses import Response

from app.core.http_limit import RateLimiter, ip_identifier


async def _run() -> None:
    FastAPILimiter.redis = SimpleNamespace(evalsha=AsyncMock(return_value=0))
    FastAPILimiter.prefix = "t"
    FastAPILimiter.identifier = ip_identifier
    FastAPILimiter.http_callback = lambda *a, **k: None
    FastAPILimiter.lua_sha = "x"

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
    FastAPILimiter.redis.evalsha.assert_awaited()
    print("ok: limiter ignores routes without .path")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
