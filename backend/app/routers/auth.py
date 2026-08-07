from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.auth import create_access_token, verify_password
from backend.app.db import get_session
from backend.app.models import StaffUser
from backend.app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    result = await session.exec(
        select(StaffUser).where(StaffUser.username == credentials.username)
    )
    staff_user = result.first()
    if staff_user is None or not verify_password(
        credentials.password, staff_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return LoginResponse(
        access_token=create_access_token(str(staff_user.id), staff_user.role),
        role=staff_user.role,
    )
