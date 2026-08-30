import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.config import settings
from backend.app.db import get_session
from backend.app.deps import require_agent_api_key
from backend.app.models import Appointment
from backend.app.schemas import (
    AppointmentCancelByCodeRequest,
    AppointmentCancelResponse,
    AppointmentCreateRequest,
    AppointmentCreateResponse,
    AppointmentTokenResponse,
)
from backend.app.services.appointments import (
    cancel_appointment,
    cancel_appointment_by_booking_code,
    create_appointment,
    get_appointment_by_token,
    qr_payload,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


def as_create_response(appointment: Appointment) -> AppointmentCreateResponse:
    return AppointmentCreateResponse(
        id=appointment.id,
        booking_code=appointment.booking_code,
        access_token=appointment.access_token,
        appointment_date=appointment.appointment_date,
        status=appointment.status,
        magic_url=f"{settings.public_web_base.rstrip('/')}/j/{appointment.access_token}",
        qr_payload=qr_payload(appointment),
    )


@router.post(
    "",
    response_model=AppointmentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_agent_api_key)],
)
async def create(
    payload: AppointmentCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppointmentCreateResponse:
    appointment = await create_appointment(
        session,
        antrian_service_id=payload.antrian_service_id,
        full_name=payload.full_name,
        document_number=payload.document_number,
        appointment_date=payload.appointment_date,
        telegram_user_id=payload.telegram_user_id,
    )
    return as_create_response(appointment)


@router.get("/by-token/{token}", response_model=AppointmentTokenResponse)
async def by_token(
    token: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppointmentTokenResponse:
    appointment = await get_appointment_by_token(session, access_token=token)
    return AppointmentTokenResponse(
        id=appointment.id,
        booking_code=appointment.booking_code,
        antrian_service_id=appointment.antrian_service_id,
        full_name=appointment.full_name,
        appointment_date=appointment.appointment_date,
        status=appointment.status,
        qr_payload=qr_payload(appointment),
    )


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentCancelResponse,
    dependencies=[Depends(require_agent_api_key)],
)
async def cancel(
    appointment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppointmentCancelResponse:
    appointment = await cancel_appointment(session, appointment_id=appointment_id)
    return AppointmentCancelResponse(
        id=appointment.id,
        booking_code=appointment.booking_code,
        status=appointment.status,
    )


@router.post(
    "/cancel-by-code",
    response_model=AppointmentCancelResponse,
    dependencies=[Depends(require_agent_api_key)],
)
async def cancel_by_code(
    payload: AppointmentCancelByCodeRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppointmentCancelResponse:
    appointment = await cancel_appointment_by_booking_code(
        session, booking_code=payload.booking_code
    )
    return AppointmentCancelResponse(
        id=appointment.id,
        booking_code=appointment.booking_code,
        status=appointment.status,
    )
