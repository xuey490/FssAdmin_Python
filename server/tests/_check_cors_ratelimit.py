"""ponytail: assert CORS / rate-limit settings wiring from env."""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "dev")

from app.config.setting import get_settings
from app.core.http_limit import ip_identifier
from app.core.middlewares import CustomCORSMiddleware


def main() -> None:
    get_settings.cache_clear()
    s = get_settings()

    assert isinstance(s.RATE_LIMIT_ENABLED, bool)
    assert s.RATE_LIMIT_TIMES == 1000
    assert s.RATE_LIMIT_SECONDS == 60
    assert isinstance(s.ALLOWED_ORIGINS, list) and len(s.ALLOWED_ORIGINS) >= 1
    assert all(isinstance(o, str) and o for o in s.ALLOWED_ORIGINS)

    names = [m for m in s.MIDDLEWARE_LIST if m]
    assert any(m and m.endswith("CustomCORSMiddleware") for m in names), names
    assert CustomCORSMiddleware is not None
    assert callable(ip_identifier)

    print(
        "ok",
        "RATE_LIMIT_ENABLED=",
        s.RATE_LIMIT_ENABLED,
        "ALLOWED_ORIGINS=",
        s.ALLOWED_ORIGINS,
    )


if __name__ == "__main__":
    main()
