from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.workflow import WorkflowRunResponse


class FailureBase(BaseModel):
    failed_job_name: str
    category: str
    severity: str
    error_signature: str
    summary: str


class FailureResponse(FailureBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_run_id: str
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int
    status: str
    workflow_run: Optional[WorkflowRunResponse] = None


class FailureDetailResponse(FailureResponse):
    log_excerpt: Optional[str] = None
    stack_trace: Optional[str] = None
    analysis_status: Optional[str] = None
    latest_analysis_id: Optional[str] = None
    latest_fix_proposal_id: Optional[str] = None
