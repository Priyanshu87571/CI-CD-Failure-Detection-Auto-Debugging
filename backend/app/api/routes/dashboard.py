from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.analytics import DashboardSummaryResponse, AnalyticsTrendResponse
from backend.app.services.analytics_service import AnalyticsService
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve top-level operational metrics and recent failure events."""
    return await AnalyticsService.get_dashboard_summary(db, workspace_id=workspace_id)


@router.get("/trends", response_model=AnalyticsTrendResponse)
async def get_analytics_trends(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical failure trends, MTTR, and verification breakdown."""
    return await AnalyticsService.get_analytics_trends(db, workspace_id=workspace_id)
