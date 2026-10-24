from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole
from backend.app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all workspaces the authenticated user belongs to."""
    query = (
        select(Workspace)
        .join(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    workspaces = res.scalars().all()
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    ws_in: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace."""
    ws = Workspace(name=ws_in.name, owner_id=current_user.id)
    db.add(ws)
    await db.flush()

    membership = WorkspaceMembership(
        workspace_id=ws.id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER,
    )
    db.add(membership)
    await db.commit()
    return WorkspaceResponse.model_validate(ws)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get single workspace details."""
    query = (
        select(Workspace)
        .join(WorkspaceMembership)
        .where(Workspace.id == workspace_id, WorkspaceMembership.user_id == current_user.id)
    )
    res = await db.execute(query)
    ws = res.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return WorkspaceResponse.model_validate(ws)
