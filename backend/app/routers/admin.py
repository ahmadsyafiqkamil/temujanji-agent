from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.db import get_session
from backend.app.deps import require_admin
from backend.app.models import Appointment, AppointmentStatus, DailyQuota, ServiceCache
from backend.app.schemas import (
    AdminAppointmentResponse,
    QuotaCreateRequest,
    QuotaResponse,
    QuotaUpdateRequest,
    ServiceResponse,
)
from backend.app.services.appointments import qr_payload
from backend.app.services.quota import create_quota, update_quota_capacity

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def as_quota_response(quota: DailyQuota) -> QuotaResponse:
    assert quota.id is not None
    return QuotaResponse(
        id=quota.id,
        antrian_service_id=quota.antrian_service_id,
        day=quota.day,
        capacity=quota.capacity,
        booked_count=quota.booked_count,
    )


def as_admin_appointment_response(appointment: Appointment) -> AdminAppointmentResponse:
    return AdminAppointmentResponse(
        id=appointment.id,
        booking_code=appointment.booking_code,
        antrian_service_id=appointment.antrian_service_id,
        full_name=appointment.full_name,
        appointment_date=appointment.appointment_date,
        status=appointment.status,
        qr_payload=qr_payload(appointment),
    )


@router.get("/appointments", response_model=list[AdminAppointmentResponse])
async def list_appointments(
    session: Annotated[AsyncSession, Depends(get_session)],
    appointment_date: Annotated[date | None, Query(alias="date")] = None,
    service_id: int | None = None,
    appointment_status: Annotated[
        AppointmentStatus | None, Query(alias="status")
    ] = None,
) -> list[AdminAppointmentResponse]:
    statement = select(Appointment)
    if appointment_date is not None:
        statement = statement.where(Appointment.appointment_date == appointment_date)
    if service_id is not None:
        statement = statement.where(Appointment.antrian_service_id == service_id)
    if appointment_status is not None:
        statement = statement.where(Appointment.status == appointment_status)
    appointments = (
        await session.exec(
            statement.order_by(Appointment.appointment_date, Appointment.created_at)
        )
    ).all()
    return [as_admin_appointment_response(appointment) for appointment in appointments]


@router.get("/services", response_model=list[ServiceResponse])
async def list_admin_services(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ServiceResponse]:
    services = (
        await session.exec(
            select(ServiceCache)
            .where(ServiceCache.is_active.is_(True))
            .order_by(ServiceCache.name)
        )
    ).all()
    return [
        ServiceResponse(
            antrian_service_id=service.antrian_service_id,
            code=service.code,
            name=service.name,
            is_active=service.is_active,
        )
        for service in services
    ]


@router.get("/quotas", response_model=list[QuotaResponse])
async def list_quotas(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[QuotaResponse]:
    quotas = (
        await session.exec(
            select(DailyQuota).order_by(
                DailyQuota.day,
                DailyQuota.antrian_service_id,
            )
        )
    ).all()
    return [as_quota_response(quota) for quota in quotas]


@router.post(
    "/quotas",
    response_model=QuotaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_quota(
    payload: QuotaCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> QuotaResponse:
    quota = await create_quota(
        session,
        antrian_service_id=payload.antrian_service_id,
        day=payload.day,
        capacity=payload.capacity,
    )
    return as_quota_response(quota)


@router.patch("/quotas/{quota_id}", response_model=QuotaResponse)
async def update_quota(
    quota_id: int,
    payload: QuotaUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> QuotaResponse:
    quota = await update_quota_capacity(
        session,
        quota_id=quota_id,
        capacity=payload.capacity,
    )
    return as_quota_response(quota)


@router.delete("/quotas/{quota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quota(
    quota_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    quota = await session.get(DailyQuota, quota_id)
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quota not found",
        )
    if quota.booked_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a quota with bookings",
        )

    await session.delete(quota)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
