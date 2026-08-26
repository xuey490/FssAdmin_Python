from datetime import datetime

from app.api.v1.module_system.role.crud import RoleCRUD
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import UserModel
from .schema import (
    UserCreateSchema,
    UserUpdateSchema,
)


class UserCRUD(CRUDBase[UserModel, UserCreateSchema, UserUpdateSchema]):
    """用户模块数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=UserModel, auth=auth)

    async def update_last_login(self, id: int) -> None:
        """
        更新用户最后登录时间

        参数:
        - id (int): 用户ID
        """
        await self.set([id], last_login=datetime.now())

    async def set_user_roles(self, user_ids: list[int], role_ids: list[int]) -> None:
        """
        批量设置用户角色

        参数:
        - user_ids (list[int]): 用户ID列表
        - role_ids (list[int]): 角色ID列表

        返回:
        - None
        """
        user_objs = await self.get_list(search={"id": ("in", user_ids)})
        if role_ids:
            role_objs = await RoleCRUD(self.auth).get_list(search={"id": ("in", role_ids)})
        else:
            role_objs = []

        for obj in user_objs:
            relationship = obj.roles
            relationship.clear()
            relationship.extend(role_objs)
        await self.auth.db.flush()

    async def change_password(self, id: int, password_hash: str) -> UserModel:
        """
        修改用户密码

        参数:
        - id (int): 用户ID
        - password_hash (str): 密码哈希值

        返回:
        - UserModel: 更新后的用户信息
        """
        return await self.update(id=id, data=UserUpdateSchema(password=password_hash))

    async def forget_password(self, id: int, password_hash: str) -> UserModel:
        """重置密码（与 change_password 逻辑相同）"""
        return await self.change_password(id=id, password_hash=password_hash)
