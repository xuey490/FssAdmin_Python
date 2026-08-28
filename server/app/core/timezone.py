"""应用时区：默认北京 Asia/Shanghai，可由 .env 的 TIMEZONE 覆盖。"""

from __future__ import annotations

import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_DEFAULT = "Asia/Shanghai"


def tz_name() -> str:
    return os.environ.get("APP_TZ") or os.environ.get("TIMEZONE") or os.environ.get("TZ") or _DEFAULT


def validate_tz_name(name: str | None) -> str:
    name = (name or "").strip() or _DEFAULT
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"无效时区: {name}") from e
    return name


def pin_process_timezone(name: str | None = None) -> None:
    """写入 TZ/APP_TZ；Linux tzset 后 datetime.now() 跟随配置时区。"""
    name = validate_tz_name(name or tz_name())
    os.environ["TZ"] = name
    os.environ["APP_TZ"] = name
    os.environ["TIMEZONE"] = name
    if hasattr(time, "tzset"):
        time.tzset()


def zone() -> ZoneInfo:
    return ZoneInfo(tz_name())


def now() -> datetime:
    """naive 当前时间（配置时区），写入 DATETIME 列。"""
    return datetime.now(zone()).replace(tzinfo=None)


def mysql_time_zone() -> str:
    """MySQL SET time_zone 用的偏移，如 +08:00。"""
    delta = datetime.now(zone()).utcoffset()
    if delta is None:
        return "+08:00"
    total = int(delta.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return f"{sign}{total // 3600:02d}:{(total % 3600) // 60:02d}"


pin_process_timezone()
