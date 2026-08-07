import httpx
from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.config import settings
from backend.app.models import Appointment, AppointmentStatus, CheckIn, StaffUser
from backend.app.services.antrian_client import AntrianClient
from backend.app.services.appointments import dubai_today
from backend.app.services.qr import verify_qr_payload


async def check_in_appointment(
    session: AsyncSession,
    *,
    qr_payload: str,
    staff_user: StaffUser,
    antrian_client: AntrianClient,
) -> Appointment:
    booking_code = verify_qr_payload(qr_payload, settings.qr_signing_secret)
    if booking_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid QR payload",
        )

    appointment = (
        await session.exec(
            select(Appointment)
            .where(Appointment.booking_code == booking_code)
            .with_for_update()
        )
    ).first()
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    if appointment.status is AppointmentStatus.CHECKED_IN:
        return appointment
    if appointment.status is not AppointmentStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked appointments can be checked in",
        )
    if appointment.appointment_date != dubai_today():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in is only allowed on the appointment date",
        )

    try:
        queue = await antrian_client.create_queue(
            appointment.antrian_service_id, appointment.booking_code
        )
        queue_id = int(queue["id"])
        queue_number = str(queue["queue_number"])
        if not queue_number:
            raise ValueError("Antrian queue number is empty")
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Antrian returned an invalid queue",
        ) from error
    except httpx.HTTPStatusError as error:
        if error.response.status_code == status.HTTP_409_CONFLICT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Antrian service is unavailable",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create queue in antrian",
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create queue in antrian",
        ) from error

    appointment.antrian_queue_id = queue_id
    appointment.queue_number = queue_number
    appointment.status = AppointmentStatus.CHECKED_IN
    session.add(appointment)
    session.add(CheckIn(appointment_id=appointment.id, staff_user_id=staff_user.id))
    await session.commit()
    await session.refresh(appointment)
    return appointment
