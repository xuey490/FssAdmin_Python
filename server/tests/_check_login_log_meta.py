"""ponytail: 登录日志要带上 UA / 属地，解析坏了这里会炸。"""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENVIRONMENT", "dev")

from app.api.v1.module_system.auth.service import AuthService
from app.api.v1.module_system.logs.service import LogService


def main() -> None:
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    )
    os_name, browser = AuthService._parse_ua(ua)
    assert os_name == "Windows", os_name
    assert browser.startswith("Chrome 151"), browser

    params = inspect.signature(LogService.write_login).parameters
    assert "os" in params and "browser" in params and "ip_location" in params
    print("login log meta ok")


if __name__ == "__main__":
    main()
