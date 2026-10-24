from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.db.session import get_db
from backend.app.core.config import settings

router = APIRouter(tags=["System Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe indicating the application process is running."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "mode": "live",
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe checking database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        return {
            "status": "unready",
            "database": f"error: {str(e)}",
        }

    return {
        "status": "ready",
        "database": db_status,
        "ai_provider": settings.AI_PROVIDER,
        "verification_runner": settings.VERIFICATION_RUNNER_TYPE,
    }
