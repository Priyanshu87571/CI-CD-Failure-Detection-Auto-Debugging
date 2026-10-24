from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class EvidenceItem(BaseModel):
    source: str = Field(description="Log file, step name, or test file")
    line_number: Optional[int] = Field(default=None, description="Line number if available")
    snippet: str = Field(description="Sanitized evidence text")
    relevance: str = Field(description="Why this evidence points to the root cause")


class AlternativeHypothesis(BaseModel):
    hypothesis: str
    likelihood: str = Field(description="low, moderate, high")
    reasoning: str


class RecommendationItem(BaseModel):
    step: int
    action: str
    command: Optional[str] = None
    target_file: Optional[str] = None


class StructuredAIAnalysisOutput(BaseModel):
    summary: str
    category: str
    root_cause: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    alternatives: List[AlternativeHypothesis] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_justification: str
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    suggested_patch: Optional[str] = Field(default=None, description="Unified diff patch if sufficient evidence exists")
    affected_files: List[str] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    failure_id: str
    status: str
    provider: str
    model: Optional[str] = None
    root_cause: str
    evidence_json: str
    alternatives_json: str
    confidence: float
    confidence_method: str
    recommendations_json: str
    token_usage: int
    estimated_cost: float
    duration_ms: int
    created_at: datetime
    parsed_evidence: Optional[List[EvidenceItem]] = None
    parsed_alternatives: Optional[List[AlternativeHypothesis]] = None
    parsed_recommendations: Optional[List[RecommendationItem]] = None
