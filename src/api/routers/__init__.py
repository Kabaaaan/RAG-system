from src.api.routers.recommendations import router as recommendations_router
from src.api.routers.vector_db import router as vector_db_router

__all__ = ["recommendations_router", "vector_db_router"]
