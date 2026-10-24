from fastapi import APIRouter
from app.api.v1.system import system_router

v1_router = APIRouter(prefix="/api/v1")

# System router is mounted at root /health and /ready in main, but can also be in v1 if needed
__all__ = ["v1_router", "system_router"]
