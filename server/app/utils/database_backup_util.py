"""数据库备份：mysqldump / pg_dump / sqlite 文件复制 → static/backup。"""

from __future__ import annotations

import gzip
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from app.config.path_conf import BACKUP_DIR, BASE_DIR
from app.config.setting import settings
from app.core.logger import logger

# ponytail: 固定保留 30 天；要可配置再加 settings 字段
DEFAULT_RETENTION_DAYS = 30


def _find_cli(name: str) -> str | None:
    return shutil.which(name)


def _cleanup_old_backups(backup_dir: Path, retention_days: int) -> int:
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for path in backup_dir.glob("*"):
        if not path.is_file():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _backup_mysql(backup_dir: Path, ts: str) -> Path:
    mysqldump = _find_cli("mysqldump")
    if not mysqldump:
        raise RuntimeError("未找到 mysqldump，请安装 MySQL 客户端并加入 PATH")

    out_path = backup_dir / f"{settings.DATABASE_NAME}_{ts}.sql.gz"
    cmd = [
        mysqldump,
        f"-h{settings.DATABASE_HOST}",
        f"-P{settings.DATABASE_PORT}",
        f"-u{settings.DATABASE_USER}",
        f"-p{settings.DATABASE_PASSWORD}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--set-gtid-purged=OFF",
        settings.DATABASE_NAME,
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"mysqldump 失败: {err}")

    with gzip.open(out_path, "wb") as f:
        f.write(proc.stdout)
    return out_path


def _backup_postgres(backup_dir: Path, ts: str) -> Path:
    pg_dump = _find_cli("pg_dump")
    if not pg_dump:
        raise RuntimeError("未找到 pg_dump，请安装 PostgreSQL 客户端并加入 PATH")

    out_path = backup_dir / f"{settings.DATABASE_NAME}_{ts}.dump"
    env = {**subprocess.os.environ, "PGPASSWORD": settings.DATABASE_PASSWORD}
    cmd = [
        pg_dump,
        "-h",
        settings.DATABASE_HOST,
        "-p",
        str(settings.DATABASE_PORT),
        "-U",
        settings.DATABASE_USER,
        "-F",
        "c",
        "-f",
        str(out_path),
        settings.DATABASE_NAME,
    ]
    proc = subprocess.run(cmd, capture_output=True, env=env, check=False)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"pg_dump 失败: {err}")
    return out_path


def _backup_sqlite(backup_dir: Path, ts: str) -> Path:
    src = BASE_DIR / f"{settings.DATABASE_NAME}.db"
    if not src.is_file():
        raise FileNotFoundError(f"SQLite 文件不存在: {src}")
    out_path = backup_dir / f"{settings.DATABASE_NAME}_{ts}.db.gz"
    with gzip.open(out_path, "wb") as f_out, open(src, "rb") as f_in:
        shutil.copyfileobj(f_in, f_out)
    return out_path


def run_database_backup(retention_days: int = DEFAULT_RETENTION_DAYS) -> dict:
    """
    执行数据库备份并清理过期文件。

    返回:
    - dict: 含 file、size_bytes、removed_old、database_type
    """
    backup_dir = BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_type = settings.DATABASE_TYPE

    if db_type == "mysql":
        out_path = _backup_mysql(backup_dir, ts)
    elif db_type == "postgres":
        out_path = _backup_postgres(backup_dir, ts)
    elif db_type == "sqlite":
        out_path = _backup_sqlite(backup_dir, ts)
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")

    removed = _cleanup_old_backups(backup_dir, retention_days)
    size = out_path.stat().st_size
    logger.info("数据库备份完成: {} ({} bytes), 清理旧文件 {} 个", out_path.name, size, removed)
    return {
        "status": "success",
        "file": str(out_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "size_bytes": size,
        "removed_old": removed,
        "database_type": db_type,
    }


if __name__ == "__main__":
    assert DEFAULT_RETENTION_DAYS >= 1
