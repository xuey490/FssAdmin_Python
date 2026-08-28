"""ponytail: 文章 data_scope 1-6 + 超管仅租户。逻辑坏了会在这里炸。不连库。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENVIRONMENT", "dev")

from sqlalchemy import select

from app.api.v1.module_platform.article.model import ArticleModel
from app.api.v1.module_platform.article.schema import ArticleCreateSchema
from app.core.data_scope import (
    DATA_SCOPE_ALL,
    DATA_SCOPE_CUSTOM,
    DATA_SCOPE_DEPT,
    DATA_SCOPE_DEPT_AND_CHILD,
    DATA_SCOPE_DEPT_AND_SELF,
    DATA_SCOPE_SELF,
    apply_scope_filters,
    resolve_scope_decision,
)
from pydantic import ValidationError


def _sql(decision) -> str:
    q = apply_scope_filters(select(ArticleModel), ArticleModel, decision)
    compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
    return compiled.split("WHERE", 1)[-1] if "WHERE" in compiled else compiled


def _base(**kwargs):
    defaults = dict(
        user_id=9,
        tenant_id=3,
        is_super=False,
        role_ids=[8],
        data_scope=DATA_SCOPE_SELF,
        dept_id=10,
        child_dept_ids=[10, 11, 12],
        custom_dept_ids=[21, 22],
    )
    defaults.update(kwargs)
    return resolve_scope_decision(**defaults)


def main() -> None:
    d = _base(user_id=None)
    assert d.deny_all
    deny_sql = _sql(d).lower()
    assert "false" in deny_sql or "0 = 1" in deny_sql or "1 = 0" in deny_sql

    d = _base(tenant_id=0)
    assert d.deny_all

    for kwargs in (
        dict(is_super=True),
        dict(user_id=1),
        dict(role_ids=[1, 8]),
        dict(data_scope=DATA_SCOPE_ALL),
    ):
        d = _base(**kwargs)
        sql = _sql(d)
        assert d.skip_business and d.tenant_id == 3 and not d.deny_all
        assert "tenant_id" in sql
        assert "created_by" not in sql
        assert "dept_id" not in sql

    d = _base(data_scope=DATA_SCOPE_DEPT)
    sql = _sql(d)
    assert d.dept_ids == (10,) and d.created_by is None
    assert "dept_id" in sql and "10" in sql and "created_by" not in sql

    d = _base(data_scope=DATA_SCOPE_DEPT, dept_id=0)
    assert d.created_by == 9 and d.dept_ids is None
    assert "created_by" in _sql(d)

    d = _base(data_scope=DATA_SCOPE_DEPT_AND_CHILD)
    sql = _sql(d)
    assert d.dept_ids == (10, 11, 12)
    assert "11" in sql and "created_by" not in sql

    d = _base(data_scope=DATA_SCOPE_DEPT_AND_CHILD, dept_id=0, child_dept_ids=[])
    assert d.created_by == 9

    d = _base(data_scope=DATA_SCOPE_SELF)
    sql = _sql(d)
    assert d.created_by == 9 and d.dept_ids is None
    assert "created_by" in sql and "9" in sql

    d = _base(data_scope=DATA_SCOPE_DEPT_AND_SELF)
    sql = _sql(d)
    assert d.or_created_by and d.created_by == 9 and 10 in d.dept_ids
    assert "created_by" in sql and "dept_id" in sql

    d = _base(data_scope=DATA_SCOPE_DEPT_AND_SELF, dept_id=0, child_dept_ids=[])
    assert d.created_by == 9 and not d.or_created_by

    d = _base(data_scope=DATA_SCOPE_CUSTOM)
    sql = _sql(d)
    assert d.dept_ids == (21, 22)
    assert "21" in sql and "created_by" not in sql

    d = _base(data_scope=DATA_SCOPE_CUSTOM, custom_dept_ids=[])
    assert d.created_by == 9 and d.dept_ids is None

    d = _base(data_scope=99)
    assert d.created_by == 9

    ArticleCreateSchema.model_validate(
        {"title": "t", "category_id": 1, "describe": "d", "content": "c", "is_link": 2}
    )
    try:
        ArticleCreateSchema.model_validate({"title": "t", "category_id": 1, "describe": "d", "is_link": 1})
        raise AssertionError("link without url should fail")
    except ValidationError:
        pass

    print("ok: article data_scope 1-6 + super tenant-only")


if __name__ == "__main__":
    main()
