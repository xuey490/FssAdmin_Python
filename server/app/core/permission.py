"""数据权限过滤（Casbin 路径已移除；保留可实例化 stub 供 CRUD 调用）。"""

from __future__ import annotations

from typing import Any


class Permission:
    def __init__(self, model: Any = None, auth: Any = None) -> None:
        self.model = model
        self.auth = auth

    async def filter_query(self, sql: Any) -> Any:
        # ponytail: 租户隔离已在 CRUDBase.__build_conditions / orm_audit 处理；此处不再加数据范围
        return sql
