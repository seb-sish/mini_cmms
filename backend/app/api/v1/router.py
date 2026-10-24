from fastapi import APIRouter
from app.api.v1.auth import auth_router
from app.api.v1.equipment import equipment_router
from app.api.v1.system import system_router
from app.api.v1.users import users_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(equipment_router)

__all__ = ["v1_router", "system_router"]
