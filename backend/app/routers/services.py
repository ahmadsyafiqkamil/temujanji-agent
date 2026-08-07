from datetime import date
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.db import get_session
from backend.app.deps import require_admin, require_agent_api_key
from backend.app.models import DailyQuota, ServiceCache, utc_now
from backend.app.schemas import (
    AvailabilityDay,
    AvailabilityResponse,
    ServiceResponse,
    ServiceSyncResponse,
)
from backend.app.services.antrian_client import AntrianClient

router = APIRouter(prefix="/services", tags=["services"])
availability_router = APIRouter(tags=["availability"])


def get_antrian_client() -> AntrianClient:
    return AntrianClient()


def as_service_response(service: ServiceCache) -> ServiceResponse:
    return ServiceResponse(
        antrian_service_id=service.antrian_service_id,
        code=service.code,
        name=service.name,
        is_active=service.is_active,
    )


@router.post(
    "/sync",
    response_model=ServiceSyncResponse,
    dependencies=[Depends(require_admin)],
)
async def sync_services(
    session: Annotated[AsyncSession, Depends(get_session)],
    antrian_client: Annotated[AntrianClient, Depends(get_antrian_client)],
) -> ServiceSyncResponse:
    try:
        source_services = await antrian_client.list_services()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to sync services from antrian",
        ) from error

    synced = 0
    for source_service in source_services:
        try:
            service_id = int(source_service["id"])
            code = str(source_service["code"])
            name = str(source_service["name"])
            is_active = bool(source_service["is_active"])
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Antrian returned an invalid service",
            ) from error

        cached_service = await session.get(ServiceCache, service_id)
        if cached_service is None:
            cached_service = ServiceCache(
                antrian_service_id=service_id,
                code=code,
                name=name,
                is_active=is_active,
            )
        else:
            cached_service.code = code
            cached_service.name = name
            cached_service.is_active = is_active
            cached_service.synced_at = utc_now()
        session.add(cached_service)
        synced += 1

    await session.commit()
    return ServiceSyncResponse(synced=synced)


@router.get(
    "",
    response_model=list[ServiceResponse],
    dependencies=[Depends(require_agent_api_key)],
)
async def list_services(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ServiceResponse]:
    services = (
        await session.exec(
            select(ServiceCache)
            .where(ServiceCache.is_active.is_(True))
            .order_by(ServiceCache.name)
        )
    ).all()
    return [as_service_response(service) for service in services]


@availability_router.get(
    "/availability",
    response_model=AvailabilityResponse,
    dependencies=[Depends(require_agent_api_key)],
)
async def get_availability(
    session: Annotated[AsyncSession, Depends(get_session)],
    service_id: int,
    from_day: Annotated[date, Query(alias="from")],
    to_day: Annotated[date, Query(alias="to")],
) -> AvailabilityResponse:
    if from_day > to_day:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="from must be on or before to",
        )

    quotas = (
        await session.exec(
            select(DailyQuota)
            .where(DailyQuota.antrian_service_id == service_id)
            .where(DailyQuota.day >= from_day)
            .where(DailyQuota.day <= to_day)
            .order_by(DailyQuota.day)
        )
    ).all()
    return AvailabilityResponse(
        service_id=service_id,
        availability=[
            AvailabilityDay(day=quota.day, remaining=quota.capacity - quota.booked_count)
            for quota in quotas
        ],
    )
