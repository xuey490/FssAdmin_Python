from app.api.v1.module_system.dept.crud import DeptCRUD
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import RoleModel
from .schema import RoleCreateSchema, RoleUpdateSchema


class RoleCRUD(CRUDBase[RoleModel, RoleCreateSchema, RoleUpdateSchema]):
    """角色模块数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=RoleModel, auth=auth)

    async def set_role_depts_crud(self, role_ids: list[int], dept_ids: list[int]) -> None:
        """
        设置角色的部门权限

        参数:
        - role_ids (list[int]): 角色ID列表
        - dept_ids (list[int]): 部门ID列表

        返回:
        - None
        """
        roles = await self.get_list(search={"id": ("in", role_ids)})
        depts = [] if not dept_ids else await DeptCRUD(self.auth).get_list(search={"id": ("in", dept_ids)})

        for obj in roles:
            relationship = obj.depts
            relationship.clear()
            relationship.extend(depts)
        await self.auth.db.flush()
