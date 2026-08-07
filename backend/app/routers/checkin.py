from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.db import get_session
from backend.app.deps import require_staff
from backend.app.models import Appointment, StaffUser
from backend.app.schemas import CheckInRequest, CheckInResponse
from backend.app.services.antrian_client import AntrianClient
from backend.app.services.checkin import check_in_appointment

router = APIRouter(tags=["check-in"])


def get_antrian_client() -> AntrianClient:
    return AntrianClient()


def as_checkin_response(appointment: Appointment) -> CheckInResponse:
    if appointment.queue_number is None:
        raise RuntimeError("Checked-in appointment has no queue number")
    return CheckInResponse(
        booking_code=appointment.booking_code,
        antrian_service_id=appointment.antrian_service_id,
        full_name=appointment.full_name,
        appointment_date=appointment.appointment_date,
        status=appointment.status,
        queue_number=appointment.queue_number,
    )


@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    payload: CheckInRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    staff_user: Annotated[StaffUser, Depends(require_staff)],
    antrian_client: Annotated[AntrianClient, Depends(get_antrian_client)],
) -> CheckInResponse:
    appointment = await check_in_appointment(
        session,
        qr_payload=payload.qr_payload,
        staff_user=staff_user,
        antrian_client=antrian_client,
    )
    return as_checkin_response(appointment)
