from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.workspace import WorkspaceMembership
from backend.app.models.repository import Repository
from backend.app.models.workflow import WorkflowRun, LogArtifact
from backend.app.schemas.workflow import WorkflowRunResponse, LogArtifactResponse
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=List[WorkflowRunResponse])
async def list_workflow_runs(
    repository_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List workflow runs scoped to user's authorized repositories."""
    query = (
        select(WorkflowRun, Repository.full_name)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(WorkspaceMembership.user_id == current_user.id)
        .order_by(WorkflowRun.created_at.desc())
    )
    if repository_id:
        query = query.where(WorkflowRun.repository_id == repository_id)

    res = await db.execute(query)
    rows = res.all()

    runs = []
    for run, repo_name in rows:
        run_dict = {
            "id": run.id,
            "repository_id": run.repository_id,
            "external_run_id": run.external_run_id,
            "workflow_name": run.workflow_name,
            "branch": run.branch,
            "commit_sha": run.commit_sha,
            "status": run.status,
            "conclusion": run.conclusion,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "created_at": run.created_at,
            "repository_name": repo_name,
        }
        runs.append(WorkflowRunResponse(**run_dict))
    return runs


@router.get("/{workflow_run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    workflow_run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workflow run details."""
    query = (
        select(WorkflowRun, Repository.full_name)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(WorkflowRun.id == workflow_run_id, WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found.")
    run, repo_name = row
    return WorkflowRunResponse(
        id=run.id,
        repository_id=run.repository_id,
        external_run_id=run.external_run_id,
        workflow_name=run.workflow_name,
        branch=run.branch,
        commit_sha=run.commit_sha,
        status=run.status,
        conclusion=run.conclusion,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        repository_name=repo_name,
    )


@router.get("/{workflow_run_id}/logs", response_model=Optional[LogArtifactResponse])
async def get_workflow_run_logs(
    workflow_run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sanitized log excerpt for a workflow run."""
    # Ensure authorized access
    query = (
        select(LogArtifact)
        .join(WorkflowRun, LogArtifact.workflow_run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repository_id == Repository.id)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(WorkflowRun.id == workflow_run_id, WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    artifact = res.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No log artifacts found for this workflow run.")
    return LogArtifactResponse.model_validate(artifact)
