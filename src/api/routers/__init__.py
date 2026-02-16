from src.api.routers.courses import router as courses_router
from src.api.routers.db import router as db_router
from src.api.routers.recommendations import router as recommendations_router
from src.api.routers.users import router as users_router

__all__ = ["courses_router", "db_router", "recommendations_router", "users_router"]
