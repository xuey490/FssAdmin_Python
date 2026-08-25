from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import TicketModel
from .schema import TicketCreateSchema, TicketUpdateSchema


class TicketCRUD(CRUDBase[TicketModel, TicketCreateSchema, TicketUpdateSchema]):
    """工单 CRUD"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=TicketModel, auth=auth)
