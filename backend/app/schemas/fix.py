from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class FixProposalCreate(BaseModel):
    analysis_id: str
    patch_content: str
    explanation: str
    affected_files: List[str] = Field(default_factory=list)


class FixApprovalRequest(BaseModel):
    approved: bool
    review_notes: Optional[str] = None


class FixProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    status: str
    patch_content: str
    explanation: str
    affected_files_json: str
    affected_files: Optional[List[str]] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
