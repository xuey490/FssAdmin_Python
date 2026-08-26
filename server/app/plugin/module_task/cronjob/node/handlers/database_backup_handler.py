"""定时任务节点：数据库备份 handler。"""

from app.utils.database_backup_util import run_database_backup


def handler(*args, **kwargs):
    retention_days = int(kwargs.get("retention_days", 30))
    return run_database_backup(retention_days=retention_days)
