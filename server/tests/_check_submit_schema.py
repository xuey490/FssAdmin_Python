"""ponytail: 主业务提交 schema 校验冒烟。逻辑坏了会在这里炸。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENVIRONMENT", "dev")

from pydantic import ValidationError

from app.api.v1.module_system.auth.schema import LoginSchema
from app.api.v1.module_system.dept.schema import DeptCreateSchema, DeptUpdateSchema
from app.api.v1.module_system.dict.schema import DictTypeCreateSchema
from app.api.v1.module_system.menu.schema import MenuCreateSchema
from app.api.v1.module_system.post.schema import PostCreateSchema
from app.api.v1.module_system.role.schema import RoleCreateSchema, RoleUpdateSchema
from app.api.v1.module_system.user.schema import UserCreateSchema, UserUpdateSchema


def _must_fail(schema, payload: dict) -> None:
    try:
        schema.model_validate(payload)
    except ValidationError:
        return
    raise AssertionError(f"{schema.__name__} should reject {payload}")


def main() -> None:
    u = UserCreateSchema.model_validate(
        {"username": "test_user", "password": "test123", "name": "测试", "dept_id": 1}
    )
    dumped = u.model_dump(exclude_none=True)
    assert dumped["username"] == "test_user"
    assert dumped["realname"] == "测试"
    assert dumped["dept_id"] == 1

    uu = UserUpdateSchema.model_validate({"name": "更新用户"})
    assert uu.model_dump(exclude_unset=True) == {"realname": "更新用户"}

    _must_fail(UserCreateSchema, {"username": "1bad", "password": "test123"})
    _must_fail(UserCreateSchema, {"username": "ok_user", "password": "123"})

    d = DeptCreateSchema.model_validate({"name": "测试部门", "parent_id": 0, "sort": 1})
    assert d.name == "测试部门"
    assert d.code is None
    _must_fail(DeptCreateSchema, {"name": "  "})
    du = DeptUpdateSchema.model_validate({"name": "更新部门"})
    assert "code" not in du.model_dump(exclude_unset=True)

    r = RoleCreateSchema.model_validate({"name": "测试角色", "code": "test_role", "sort": 1})
    assert r.sort == 1
    ru = RoleUpdateSchema.model_validate({"name": "更新角色"})
    assert ru.model_dump(exclude_unset=True) == {"name": "更新角色"}
    _must_fail(RoleCreateSchema, {"name": "x", "code": "1bad"})

    m = MenuCreateSchema.model_validate({"name": "首页", "type": 1})
    assert m.type == 1
    _must_fail(MenuCreateSchema, {"name": "页", "type": 2})
    MenuCreateSchema.model_validate({"name": "页", "type": 2, "path": "/x", "component": "views/x"})
    _must_fail(MenuCreateSchema, {"name": "外链", "type": 4})

    PostCreateSchema.model_validate({"name": "开发", "code": "dev_post"})
    _must_fail(PostCreateSchema, {"name": "开发", "code": ""})

    DictTypeCreateSchema.model_validate({"dict_name": "测试字典", "dict_type": "test_dict", "status": 0})
    _must_fail(DictTypeCreateSchema, {"dict_name": "x"})

    LoginSchema.model_validate({"username": "admin", "password": "123456", "tenant_id": 1})
    _must_fail(LoginSchema, {"username": "", "password": "x"})

    print("submit schema ok")


if __name__ == "__main__":
    main()
