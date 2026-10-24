from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class VerificationTriggerRequest(BaseModel):
    allow_sandbox_execution: bool = True
    test_command: Optional[str] = None


class VerificationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fix_proposal_id: str
    status: str  # not_run, running, passed, failed, timed_out, cancelled, unavailable, inconclusive
    test_summary_json: str
    exit_code: Optional[int] = None
    duration_ms: int
    baseline_result: Optional[str] = None
    candidate_result: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    parsed_test_summary: Optional[Dict[str, Any]] = None
