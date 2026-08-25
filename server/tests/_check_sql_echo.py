"""ponytail: assert SQL echo settings + install hook."""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "dev")

from app.config.setting import get_settings
from app.core.sql_echo import _format_sql, install_sql_echo


def main() -> None:
    get_settings.cache_clear()
    s = get_settings()
    assert hasattr(s, "SQL_ECHO_CONSOLE")
    assert hasattr(s, "SQL_ECHO_FILE")
    line = _format_sql("SELECT 1", (1,))
    assert "SELECT 1" in line and "params=" in line
    # install is no-op when both false
    from app.core.database import async_engine

    install_sql_echo(async_engine)
    print("ok", "SQL_ECHO_CONSOLE=", s.SQL_ECHO_CONSOLE, "SQL_ECHO_FILE=", s.SQL_ECHO_FILE)


if __name__ == "__main__":
    main()
