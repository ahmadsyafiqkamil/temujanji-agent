from pydantic import BaseModel, Field

from backend.app.models import StaffRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    role: StaffRole
    token_type: str = "bearer"
