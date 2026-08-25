from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import PluginModel
from .schema import PluginCreateSchema, PluginUpdateSchema


class PluginCRUD(CRUDBase[PluginModel, PluginCreateSchema, PluginUpdateSchema]):
    """插件数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=PluginModel, auth=auth)
