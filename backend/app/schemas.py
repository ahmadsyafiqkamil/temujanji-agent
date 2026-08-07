import uuid
from datetime import date

from pydantic import BaseModel, Field

from backend.app.models import AppointmentStatus, StaffRole


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


class AppointmentCreateRequest(BaseModel):
    antrian_service_id: int
    full_name: str = Field(min_length=1, max_length=255)
    document_number: str = Field(min_length=1, max_length=128)
    appointment_date: date
    telegram_user_id: str | None = Field(default=None, max_length=128)


class AppointmentCreateResponse(BaseModel):
    id: uuid.UUID
    booking_code: str
    access_token: str
    appointment_date: date
    status: AppointmentStatus
    magic_url: str


class AppointmentTokenResponse(BaseModel):
    id: uuid.UUID
    booking_code: str
    antrian_service_id: int
    full_name: str
    appointment_date: date
    status: AppointmentStatus
    qr_payload: str


class AdminAppointmentResponse(BaseModel):
    id: uuid.UUID
    booking_code: str
    antrian_service_id: int
    full_name: str
    appointment_date: date
    status: AppointmentStatus
    qr_payload: str


class AppointmentCancelResponse(BaseModel):
    id: uuid.UUID
    booking_code: str
    status: AppointmentStatus


class AppointmentCancelByCodeRequest(BaseModel):
    booking_code: str = Field(min_length=1, max_length=64)


class CheckInRequest(BaseModel):
    qr_payload: str = Field(min_length=1)


class CheckInResponse(BaseModel):
    booking_code: str
    antrian_service_id: int
    full_name: str
    appointment_date: date
    status: AppointmentStatus
    queue_number: str
