from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.session import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.user import User
from backend.app.models.workspace import WorkspaceMembership, WorkspaceRole

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_workspace_role(min_role: WorkspaceRole):
    async def role_checker(
        workspace_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> WorkspaceMembership:
        query = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == current_user.id
        )
        res = await db.execute(query)
        membership = res.scalar_one_or_none()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace"
            )
        
        role_hierarchy = {
            WorkspaceRole.MEMBER: 1,
            WorkspaceRole.ADMIN: 2,
            WorkspaceRole.OWNER: 3,
        }
        user_rank = role_hierarchy.get(membership.role, 0)
        required_rank = role_hierarchy.get(min_role, 1)

        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient workspace permissions. Required: {min_role.value}"
            )
        return membership
    return role_checker
