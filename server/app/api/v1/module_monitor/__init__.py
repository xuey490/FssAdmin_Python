from fastapi import APIRouter

from app.api.v1.module_monitor.core_server import CoreServerRouter
from app.api.v1.module_monitor.database import DatabaseRouter
from app.api.v1.module_monitor.online import OnlineRouter

monitor_router = APIRouter()
monitor_router.include_router(OnlineRouter)

__all__ = ["monitor_router", "CoreServerRouter", "DatabaseRouter", "OnlineRouter"]
