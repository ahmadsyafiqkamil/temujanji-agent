from datetime import date

from pydantic import BaseModel, Field

from backend.app.models import StaffRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    role: StaffRole
    token_type: str = "bearer"


class ServiceResponse(BaseModel):
    antrian_service_id: int
    code: str
    name: str
    is_active: bool


class ServiceSyncResponse(BaseModel):
    synced: int


class QuotaCreateRequest(BaseModel):
    antrian_service_id: int
    day: date
    capacity: int = Field(ge=1)


class QuotaUpdateRequest(BaseModel):
    capacity: int = Field(ge=1)


class QuotaResponse(BaseModel):
    id: int
    antrian_service_id: int
    day: date
    capacity: int
    booked_count: int


class AvailabilityDay(BaseModel):
    day: date
    remaining: int


class AvailabilityResponse(BaseModel):
    service_id: int
    availability: list[AvailabilityDay]
