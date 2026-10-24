from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class FailureCategoryStat(BaseModel):
    category: str
    count: int
    percentage: float


class DailyFailureTrend(BaseModel):
    date: str
    total_runs: int
    failed_runs: int
    failure_rate: float


class DashboardSummaryResponse(BaseModel):
    monitored_repositories_count: int
    total_workflow_runs_count: int
    failed_workflow_runs_count: int
    failure_rate_percent: float
    analyses_completed_count: int
    fix_verification_pass_rate_percent: float
    open_failures_count: int
    verified_fixes_count: int
    recent_failures: List[Dict[str, Any]]
    top_failure_categories: List[FailureCategoryStat]


class AnalyticsTrendResponse(BaseModel):
    daily_trends: List[DailyFailureTrend]
    category_distribution: List[FailureCategoryStat]
    average_mttr_minutes: Optional[float] = None
    verification_outcomes: Dict[str, int]
    ai_cost_and_tokens: Dict[str, Any]
