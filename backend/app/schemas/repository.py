from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class RepositoryCreate(BaseModel):
    workspace_id: str
    full_name: str = Field(description="Format: owner/repo")
    default_branch: str = "main"
    provider: str = "github"
    external_repository_id: Optional[str] = None
    installation_reference: Optional[str] = None


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    provider: str
    external_repository_id: Optional[str] = None
    full_name: str
    default_branch: str
    connection_status: str
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    workflow_runs_count: Optional[int] = 0
    failure_count: Optional[int] = 0


class RepositorySyncRequest(BaseModel):
    force: bool = False
