from datetime import date

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.models import DailyQuota, ServiceCache


async def create_quota(
    session: AsyncSession,
    *,
    antrian_service_id: int,
    day: date,
    capacity: int,
) -> DailyQuota:
    service = await session.get(ServiceCache, antrian_service_id)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    existing = (
        await session.exec(
            select(DailyQuota).where(
                DailyQuota.antrian_service_id == antrian_service_id,
                DailyQuota.day == day,
            )
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quota already exists for this service and day",
        )

    quota = DailyQuota(
        antrian_service_id=antrian_service_id,
        day=day,
        capacity=capacity,
    )
    session.add(quota)
    await session.commit()
    await session.refresh(quota)
    return quota


async def update_quota_capacity(
    session: AsyncSession,
    *,
    quota_id: int,
    capacity: int,
) -> DailyQuota:
    quota = await session.get(DailyQuota, quota_id)
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quota not found",
        )
    if capacity < quota.booked_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Capacity cannot be below booked_count",
        )

    quota.capacity = capacity
    session.add(quota)
    await session.commit()
    await session.refresh(quota)
    return quota
