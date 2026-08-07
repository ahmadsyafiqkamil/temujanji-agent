import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.auth import decode_access_token
from backend.app.config import settings
from backend.app.db import get_session
from backend.app.models import StaffRole, StaffUser

bearer_scheme = HTTPBearer(auto_error=False)


async def require_agent_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if x_api_key is None or not secrets.compare_digest(
        x_api_key, settings.agent_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent API key",
        )


async def require_staff(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StaffUser:
    """Require an authenticated staff-facing user; admins are a staff superset."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        staff_user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
        ) from None

    staff_user = await session.get(StaffUser, staff_user_id)
    if staff_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff user not found",
        )
    return staff_user


async def require_admin(
    staff_user: Annotated[StaffUser, Depends(require_staff)],
) -> StaffUser:
    if staff_user.role is not StaffRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return staff_user
