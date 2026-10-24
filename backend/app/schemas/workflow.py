from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    external_run_id: str
    workflow_name: str
    branch: str
    commit_sha: str
    status: str
    conclusion: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    repository_name: Optional[str] = None


class LogArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_run_id: str
    sanitized_excerpt: str
    content_hash: str
    created_at: datetime
