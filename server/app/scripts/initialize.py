"""
数据库初始化：空库时导入 FastAdmin/database/fssoa.sql。
已存在 sa_system_user 表则跳过；导入后不再单独写种子数据。
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import text

from app.config.path_conf import BASE_DIR
from app.config.setting import settings
from app.core.database import async_engine
from app.core.logger import logger

FSSOA_SQL = BASE_DIR / "database" / "fssoa.sql"


def _split_mysql_statements(sql: str) -> list[str]:
    """按分号拆分，尊重单/双引号与反斜杠转义（避免 HTML 内容中的 ; 误切）。"""
    stmts: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    escape = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if escape:
            buf.append(ch)
            escape = False
            i += 1
            continue
        if ch == "\\" and (in_single or in_double):
            buf.append(ch)
            escape = True
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            if stmt and not stmt.startswith("--"):
                stmts.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


async def _table_exists(conn) -> bool:
    exists = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'sa_system_user'"
        )
    )
    return int(exists.scalar() or 0) > 0


def _import_via_mysql_cli(sql_path: Path) -> bool:
    mysql = shutil.which("mysql")
    if not mysql:
        return False
    cmd = [
        mysql,
        f"-h{settings.DATABASE_HOST}",
        f"-P{settings.DATABASE_PORT}",
        f"-u{settings.DATABASE_USER}",
        f"-p{settings.DATABASE_PASSWORD}",
        "--default-character-set=utf8mb4",
        settings.DATABASE_NAME,
    ]
    raw = sql_path.read_text(encoding="utf-8")
    raw = re.sub(r"(?im)^\s*USE\s+[`'\"]?\w+[`'\"]?\s*;?\s*$", "", raw)
    try:
        proc = subprocess.run(
            cmd,
            input=raw.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            logger.error("mysql cli 导入失败: {}", proc.stderr.decode("utf-8", errors="ignore")[:500])
            return False
        return True
    except Exception as e:
        logger.error("mysql cli 调用失败: {}", e)
        return False


class InitializeData:
    """导入 fssoa.sql 初始化数据库（无额外种子写操作）。"""

    async def init_db(self) -> None:
        if not FSSOA_SQL.exists():
            raise FileNotFoundError(f"初始化 SQL 不存在: {FSSOA_SQL}")

        async with async_engine.begin() as conn:
            if await _table_exists(conn):
                logger.info("sa_system_user 已有数据，跳过 fssoa.sql 导入")
                return

        logger.info("开始导入 {}", FSSOA_SQL)
        ok = await asyncio.to_thread(_import_via_mysql_cli, FSSOA_SQL)
        if ok:
            logger.info("fssoa.sql 经 mysql cli 导入完成")
            return

        sql_text = FSSOA_SQL.read_text(encoding="utf-8")
        sql_text = re.sub(r"(?im)^\s*USE\s+[`'\"]?\w+[`'\"]?\s*;?\s*$", "", sql_text)
        statements = _split_mysql_statements(sql_text)
        async with async_engine.begin() as conn:
            await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            for i, stmt in enumerate(statements, 1):
                upper = stmt.lstrip().upper()
                if upper.startswith("CREATE DATABASE") or upper.startswith("DROP DATABASE"):
                    continue
                if upper.startswith("--"):
                    continue
                try:
                    # asyncmy 会把 % 当格式化占位符；dump 中 HTML/JSON 含 % 需转义
                    await conn.exec_driver_sql(stmt.replace("%", "%%"))
                except Exception as e:
                    msg = str(e).lower()
                    if any(
                        x in msg
                        for x in (
                            "already exists",
                            "unknown table",
                            "duplicate entry",
                            "column count doesn't match",
                            "1062",
                            "1050",
                            "1136",
                            "bind parameter",
                        )
                    ):
                        continue
                    logger.error("执行第 {} 条 SQL 失败: {}", i, e)
                    raise
            await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        logger.info("fssoa.sql 导入完成（{} 条语句）", len(statements))
