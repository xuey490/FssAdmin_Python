"""ponytail: TIMEZONE 默认北京；now() naive 且贴近配置时区。"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENVIRONMENT", "dev")

from app.config.setting import settings
from app.core.timezone import mysql_time_zone, now, tz_name, validate_tz_name


def main() -> None:
    assert settings.TIMEZONE == "Asia/Shanghai"
    assert tz_name() == "Asia/Shanghai"
    assert mysql_time_zone() == "+08:00"
    n = now()
    assert n.tzinfo is None
    sh = datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
    assert abs((sh - n).total_seconds()) < 2
    try:
        validate_tz_name("Not/AZone")
        raise AssertionError("invalid tz should fail")
    except ValueError:
        pass
    print("ok: TIMEZONE from settings default Asia/Shanghai")


if __name__ == "__main__":
    main()
