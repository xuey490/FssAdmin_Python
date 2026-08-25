from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import TenantModel
from .schema import TenantCreateSchema, TenantUpdateSchema


class TenantCRUD(CRUDBase[TenantModel, TenantCreateSchema, TenantUpdateSchema]):
    """租户数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=TenantModel, auth=auth)
