from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.db.session import engine
from backend.app.db.base import Base
import backend.app.models  # Ensure all models are registered

# Import routers
from backend.app.api.routes import (
    health,
    auth,
    workspaces,
    repositories,
    workflows,
    failures,
    fixes,
    dashboard,
    webhooks,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode...")
    
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized.")

    # No demo users, repositories, or fixture data are created on startup.

    yield
    
    # Graceful shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI-Powered CI/CD Failure Detection, Root-Cause Analysis & Auto-Debugging Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler protecting sensitive internal exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )


# Include API v1 Routers
api_v1 = settings.API_V1_PREFIX
app.include_router(health.router, prefix=api_v1)
app.include_router(auth.router, prefix=api_v1)
app.include_router(workspaces.router, prefix=api_v1)
app.include_router(repositories.router, prefix=api_v1)
app.include_router(workflows.router, prefix=api_v1)
app.include_router(failures.router, prefix=api_v1)
app.include_router(fixes.router, prefix=api_v1)
app.include_router(dashboard.router, prefix=api_v1)
app.include_router(webhooks.router, prefix=api_v1)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": f"{api_v1}/health",
        "mode": "live",
    }
