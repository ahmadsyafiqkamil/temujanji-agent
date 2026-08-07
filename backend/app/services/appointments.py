import secrets
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.config import settings
from backend.app.models import Appointment, AppointmentStatus, DailyQuota, ServiceCache
from backend.app.services.qr import make_qr_payload


def new_booking_code() -> str:
    return f"KJRI-{secrets.token_hex(4).upper()}"


def new_access_token() -> str:
    return secrets.token_urlsafe(32)


def dubai_today() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()


async def create_appointment(
    session: AsyncSession,
    *,
    antrian_service_id: int,
    full_name: str,
    document_number: str,
    appointment_date: date,
    telegram_user_id: str | None,
) -> Appointment:
    if appointment_date < dubai_today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment date cannot be in the past",
        )

    service = await session.get(ServiceCache, antrian_service_id)
    if service is None or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is unavailable",
        )

    quota = (
        await session.exec(
            select(DailyQuota)
            .where(DailyQuota.antrian_service_id == antrian_service_id)
            .where(DailyQuota.day == appointment_date)
            .with_for_update()
        )
    ).first()
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quota is not open for this service and day",
        )

    existing = (
        await session.exec(
            select(Appointment)
            .where(Appointment.document_number == document_number)
            .where(Appointment.antrian_service_id == antrian_service_id)
            .where(Appointment.appointment_date == appointment_date)
            .where(Appointment.status == AppointmentStatus.BOOKED)
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active appointment already exists",
        )
    if quota.booked_count >= quota.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quota is full",
        )

    appointment = Appointment(
        booking_code=new_booking_code(),
        access_token=new_access_token(),
        antrian_service_id=antrian_service_id,
        full_name=full_name,
        document_number=document_number,
        appointment_date=appointment_date,
        telegram_user_id=telegram_user_id,
    )
    quota.booked_count += 1
    session.add(appointment)
    session.add(quota)
    await session.commit()
    await session.refresh(appointment)
    return appointment


async def get_appointment_by_token(
    session: AsyncSession, *, access_token: str
) -> Appointment:
    appointment = (
        await session.exec(
            select(Appointment).where(Appointment.access_token == access_token)
        )
    ).first()
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    return appointment


async def cancel_appointment(
    session: AsyncSession, *, appointment_id: uuid.UUID
) -> Appointment:
    appointment = (
        await session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )
    ).first()
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    if appointment.status is not AppointmentStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked appointments can be cancelled",
        )

    quota = (
        await session.exec(
            select(DailyQuota)
            .where(DailyQuota.antrian_service_id == appointment.antrian_service_id)
            .where(DailyQuota.day == appointment.appointment_date)
            .with_for_update()
        )
    ).first()
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment quota is unavailable",
        )

    appointment.status = AppointmentStatus.CANCELLED
    quota.booked_count -= 1
    session.add(appointment)
    session.add(quota)
    await session.commit()
    await session.refresh(appointment)
    return appointment


def qr_payload(appointment: Appointment) -> str:
    return make_qr_payload(appointment.booking_code, settings.qr_signing_secret)
