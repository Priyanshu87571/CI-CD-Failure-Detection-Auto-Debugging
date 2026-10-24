from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.workspace import WorkspaceMembership, WorkspaceRole
from backend.app.models.repository import Repository
from backend.app.models.workflow import WorkflowRun
from backend.app.models.failure import Failure
from backend.app.schemas.repository import RepositoryCreate, RepositoryResponse, RepositorySyncRequest
from backend.app.services.github_service import GitHubService
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List monitored repositories with counts."""
    # Enforce workspace membership
    query = (
        select(Repository)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(WorkspaceMembership.user_id == current_user.id)
    )
    if workspace_id:
        query = query.where(Repository.workspace_id == workspace_id)

    res = await db.execute(query)
    repos = res.scalars().all()

    response_list = []
    for r in repos:
        runs_count = (await db.execute(select(func.count(WorkflowRun.id)).where(WorkflowRun.repository_id == r.id))).scalar() or 0
        fail_count = (await db.execute(
            select(func.count(Failure.id)).join(WorkflowRun).where(WorkflowRun.repository_id == r.id)
        )).scalar() or 0

        repo_dict = {
            "id": r.id,
            "workspace_id": r.workspace_id,
            "provider": r.provider,
            "external_repository_id": r.external_repository_id,
            "full_name": r.full_name,
            "default_branch": r.default_branch,
            "connection_status": r.connection_status,
            "last_synced_at": r.last_synced_at,
            "created_at": r.created_at,
            "workflow_runs_count": runs_count,
            "failure_count": fail_count,
        }
        response_list.append(RepositoryResponse(**repo_dict))

    return response_list


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def connect_repository(
    repo_in: RepositoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect a new repository to workspace."""
    # Check membership
    mem = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == repo_in.workspace_id,
            WorkspaceMembership.user_id == current_user.id
        )
    )
    if not mem.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this workspace.")

    # Normalize full GitHub URL or owner/repo input before persistence.
    try:
        repo_in.full_name = GitHubService.normalize_repo(repo_in.full_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # Check duplicate
    existing = await db.execute(
        select(Repository).where(
            Repository.workspace_id == repo_in.workspace_id,
            Repository.full_name == repo_in.full_name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository already connected to this workspace.")

    repo = Repository(
        workspace_id=repo_in.workspace_id,
        full_name=repo_in.full_name,
        default_branch=repo_in.default_branch,
        provider=repo_in.provider,
        connection_status="connected",
    )
    db.add(repo)
    await db.commit()

    # Automatically sync live GitHub Actions data. Keep repository if sync fails so user can retry.
    try:
        await GitHubService.sync_repository(db, repo)
    except (ValueError, httpx.HTTPError) as exc:
        repo.connection_status = "disconnected"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    runs_count = (await db.execute(select(func.count(WorkflowRun.id)).where(WorkflowRun.repository_id == repo.id))).scalar() or 0
    fail_count = (await db.execute(select(func.count(Failure.id)).join(WorkflowRun).where(WorkflowRun.repository_id == repo.id))).scalar() or 0

    return RepositoryResponse(
        id=repo.id,
        workspace_id=repo.workspace_id,
        provider=repo.provider,
        external_repository_id=repo.external_repository_id,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        connection_status=repo.connection_status,
        last_synced_at=repo.last_synced_at,
        created_at=repo.created_at,
        workflow_runs_count=runs_count,
        failure_count=fail_count,
    )


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get single repository details."""
    query = (
        select(Repository)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(Repository.id == repository_id, WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    runs_count = (await db.execute(select(func.count(WorkflowRun.id)).where(WorkflowRun.repository_id == repo.id))).scalar() or 0
    fail_count = (await db.execute(
        select(func.count(Failure.id)).join(WorkflowRun).where(WorkflowRun.repository_id == repo.id)
    )).scalar() or 0

    return RepositoryResponse(
        id=repo.id,
        workspace_id=repo.workspace_id,
        provider=repo.provider,
        external_repository_id=repo.external_repository_id,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        connection_status=repo.connection_status,
        last_synced_at=repo.last_synced_at,
        created_at=repo.created_at,
        workflow_runs_count=runs_count,
        failure_count=fail_count,
    )


@router.post("/{repository_id}/sync")
async def sync_repository(
    repository_id: str,
    sync_req: Optional[RepositorySyncRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger synchronization of workflow runs for a repository."""
    query = (
        select(Repository)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(Repository.id == repository_id, WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    try:
        imported = await GitHubService.sync_repository(db, repo)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API request failed: {type(exc).__name__}")
    return {
        "status": "synchronized",
        "repository": repo.full_name,
        "runs_imported": imported,
        "mode": repo.connection_status,
    }


@router.delete("/{repository_id}", status_code=status.HTTP_200_OK)
async def delete_repository(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove repository from workspace."""
    query = (
        select(Repository)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Repository.workspace_id)
        .where(Repository.id == repository_id, WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    await db.delete(repo)
    await db.commit()
    return {"message": f"Repository '{repo.full_name}' successfully removed."}
