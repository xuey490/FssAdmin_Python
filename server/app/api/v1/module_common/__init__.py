from fastapi import APIRouter

from .monitoring import HealthRouter

common_router = APIRouter(prefix='/common')
common_router.include_router(HealthRouter)
