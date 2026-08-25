from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import DemoModel
from .schema import DemoCreateSchema, DemoUpdateSchema


class DemoCRUD(CRUDBase[DemoModel, DemoCreateSchema, DemoUpdateSchema]):
    """示例数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化CRUD数据层

        参数:
        - auth (AuthSchema): 认证信息模型
        """
        super().__init__(model=DemoModel, auth=auth)
