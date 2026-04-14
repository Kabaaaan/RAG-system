from src.api.routers.auth import router as auth_router
from src.api.routers.recommendations import router as recommendations_router
from src.api.routers.staging_area import router as staging_area_router
from src.api.routers.system import router as system_router
from src.api.routers.vector_db import router as vector_db_router

__all__ = [
    "auth_router",
    "recommendations_router",
    "staging_area_router",
    "system_router",
    "vector_db_router",
]
