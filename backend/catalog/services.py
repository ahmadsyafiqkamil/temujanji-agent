from datetime import date

import httpx
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from catalog.antrian_client import AntrianClient
from catalog.models import DailyQuota, ServiceCache


class Conflict(APIException):
    status_code = 409
    default_detail = "Conflict"


class BadGateway(APIException):
    status_code = 502
    default_detail = "Bad gateway"


def sync_services(client: AntrianClient | None = None) -> int:
    client = client or AntrianClient()
    try:
        source_services = client.list_services()
    except (httpx.HTTPError, ValueError) as error:
        raise BadGateway("Unable to sync services from antrian") from error

    synced = 0
    for source in source_services:
        try:
            service_id = int(source["id"])
            code = str(source["code"])
            name = str(source["name"])
            is_active = bool(source["is_active"])
        except (KeyError, TypeError, ValueError) as error:
            raise BadGateway("Antrian returned an invalid service") from error
        ServiceCache.objects.update_or_create(
            antrian_service_id=service_id,
            defaults={
                "code": code,
                "name": name,
                "is_active": is_active,
                "synced_at": timezone.now(),
            },
        )
        synced += 1
    return synced


def create_quota(*, antrian_service_id: int, day: date, capacity: int) -> DailyQuota:
    if not ServiceCache.objects.filter(pk=antrian_service_id).exists():
        raise NotFound("Service not found")
    if DailyQuota.objects.filter(
        antrian_service_id=antrian_service_id, day=day
    ).exists():
        raise Conflict("Quota already exists for this service and day")
    if capacity < 1:
        raise ValidationError({"capacity": ["Must be at least 1"]})
    return DailyQuota.objects.create(
        antrian_service_id=antrian_service_id,
        day=day,
        capacity=capacity,
    )


def update_quota(quota: DailyQuota, *, capacity: int) -> DailyQuota:
    if capacity < quota.booked_count:
        raise Conflict("Capacity cannot be below booked_count")
    quota.capacity = capacity
    quota.save(update_fields=["capacity"])
    return quota
