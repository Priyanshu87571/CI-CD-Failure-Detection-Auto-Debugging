from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class WorkspaceMemberAdd(BaseModel):
    user_id: str
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    owner_id: str
    created_at: datetime


class WorkspaceMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    created_at: datetime
