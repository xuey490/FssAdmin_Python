"""ORM SQL 回显：控制台绿色打印 / 按天写文件。"""

from __future__ import annotations

import sys
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config.path_conf import LOG_DIR
from app.config.setting import settings
from app.core.request_context import get_correlation_id

_GREEN = "\033[32m"
_RESET = "\033[0m"
_sql_file_logger = None
_installed: set[int] = set()


def _ensure_file_logger():
    global _sql_file_logger
    if _sql_file_logger is not None:
        return _sql_file_logger
    from loguru import logger as _logger

    sql_dir = LOG_DIR / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    # 独立 sink：只收 bind(sql=True) 的记录，按天切分
    sink_id = _logger.add(
        str(sql_dir / "sql_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
        level="DEBUG",
        filter=lambda r: r["extra"].get("sql") is True,
        rotation="00:00",
        retention=30,
        encoding="utf-8",
        enqueue=True,
    )
    _sql_file_logger = _logger.bind(sql=True)
    _ = sink_id
    return _sql_file_logger


def _format_sql(statement: str, parameters: Any) -> str:
    sql = " ".join(str(statement).split())
    cid = get_correlation_id()
    prefix = f"cid={cid[:8]} | " if cid else ""
    if parameters is None:
        return f"{prefix}{sql}"
    return f"{prefix}{sql} | params={parameters!r}"


def _emit(statement: str, parameters: Any) -> None:
    if not settings.SQL_ECHO_CONSOLE and not settings.SQL_ECHO_FILE:
        return
    line = _format_sql(statement, parameters)
    if settings.SQL_ECHO_CONSOLE:
        sys.stdout.write(f"{_GREEN}[SQL DEBUG] {line}{_RESET}\n")
        sys.stdout.flush()
    if settings.SQL_ECHO_FILE:
        _ensure_file_logger().info("{}", line)


def _before_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    _emit(statement, parameters)


def install_sql_echo(engine: Engine | Any) -> None:
    """挂到同步 Engine；AsyncEngine 传 sync_engine。"""
    if not settings.SQL_ECHO_CONSOLE and not settings.SQL_ECHO_FILE:
        return
    sync = getattr(engine, "sync_engine", engine)
    key = id(sync)
    if key in _installed:
        return
    event.listen(sync, "before_cursor_execute", _before_cursor_execute)
    _installed.add(key)
