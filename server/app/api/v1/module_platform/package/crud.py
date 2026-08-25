from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import PackageModel
from .schema import PackageCreateSchema, PackageUpdateSchema


class PackageCRUD(CRUDBase[PackageModel, PackageCreateSchema, PackageUpdateSchema]):
    """套餐模块 CRUD"""

    def __init__(self, auth: AuthSchema):
        super().__init__(model=PackageModel, auth=auth)
