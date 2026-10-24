from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import close_redis_pool
from app.api.v1.router import system_router, v1_router
from app.config import settings
from app.db.session import SessionManager
from app.errors.handlers import register_error_handlers

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup tasks
    yield
    # Shutdown tasks: gracefully dispose DB engine and disconnect Redis pool
    await SessionManager().close()
    await close_redis_pool()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app.SERVICE_NAME,
        version=settings.app.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register RFC 9457 ProblemDetail error handlers
    register_error_handlers(app)

    # Mount system probes at root
    app.include_router(system_router)
    # Mount business API at /api/v1
    app.include_router(v1_router)

    return app

app = create_app()

def main() -> None:
    uvicorn.run(
        "app.__main__:app",
        host=settings.app.HOST,
        port=settings.app.PORT,
        reload=False,
    )

if __name__ == "__main__":
    main()
