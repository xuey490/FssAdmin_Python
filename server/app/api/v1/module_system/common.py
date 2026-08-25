"""system 模块公共工具：序列化、树构建、软删条件。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnElement


def row_to_dict(obj: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    data: dict[str, Any] = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name, None)
        if isinstance(val, datetime):
            data[col.name] = val.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(val, date):
            data[col.name] = val.strftime("%Y-%m-%d")
        else:
            data[col.name] = val
    return data


def not_deleted(model: Any) -> ColumnElement[bool]:
    return model.delete_time.is_(None)


def build_tree(
    rows: list[dict[str, Any]],
    *,
    parent_id: int = 0,
    id_key: str = "id",
    parent_key: str = "parent_id",
    children_key: str = "children",
    promote_orphans: bool = False,
) -> list[dict[str, Any]]:
    """按 parent_id 递归建树（对齐 phpserver buildTree）。"""
    ids = {int(row.get(id_key) or 0) for row in rows}
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        pid = int(row.get(parent_key) or 0)
        # 仅部门脏数据：父节点不在结果集时挂到根
        if promote_orphans and pid != parent_id and pid not in ids:
            pid = parent_id
        by_parent.setdefault(pid, []).append(row)

    def walk(pid: int) -> list[dict[str, Any]]:
        tree: list[dict[str, Any]] = []
        for node in by_parent.get(pid, []):
            kids = walk(int(node.get(id_key) or 0))
            if kids:
                node[children_key] = kids
            else:
                node.pop(children_key, None)
            tree.append(node)
        return tree

    return walk(int(parent_id))


def status_text(status: int | None) -> str:
    return "启用" if int(status or 0) == 1 else "禁用"


def parse_page(params: dict[str, Any]) -> tuple[int, int]:
    page = max(1, int(params.get("page") or 1))
    limit = max(1, min(200, int(params.get("limit") or params.get("pageSize") or params.get("size") or 20)))
    return page, limit
