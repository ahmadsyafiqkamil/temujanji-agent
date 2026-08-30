import base64
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from appointments.qr import make_qr_payload
from catalog.models import DailyQuota, ServiceCache


def dubai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Dubai")).date()


def seed_bookable_quota(*, capacity: int = 2, booked_count: int = 0) -> DailyQuota:
    day = dubai_today()
    ServiceCache.objects.get_or_create(
        antrian_service_id=7,
        defaults={"code": "PAS", "name": "Paspor", "is_active": True},
    )
    quota, _ = DailyQuota.objects.get_or_create(
        antrian_service_id=7,
        day=day,
        defaults={"capacity": capacity, "booked_count": booked_count},
    )
    if quota.capacity != capacity or quota.booked_count != booked_count:
        quota.capacity = capacity
        quota.booked_count = booked_count
        quota.save(update_fields=["capacity", "booked_count"])
    return quota


def appointment_payload(day: date) -> dict[str, str | int]:
    return {
        "antrian_service_id": 7,
        "full_name": "Siti Aminah",
        "document_number": "A1234567",
        "appointment_date": day.isoformat(),
        "telegram_user_id": "12345",
    }


@pytest.mark.django_db
def test_create_increments_quota_and_returns_magic_url(agent_client):
    quota = seed_bookable_quota()
    response = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["booking_code"].startswith("KJRI-")
    assert body["magic_url"] == f"http://localhost:3000/j/{body['access_token']}"
    assert body["qr_payload"]
    quota.refresh_from_db()
    assert quota.booked_count == 1


@pytest.mark.django_db
def test_create_rejects_duplicate_active_booking(agent_client):
    quota = seed_bookable_quota()
    first = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )
    second = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Active appointment already exists"
    quota.refresh_from_db()
    assert quota.booked_count == 1


@pytest.mark.django_db
def test_create_allows_different_document_on_same_service_and_day(agent_client):
    quota = seed_bookable_quota()
    second_payload = appointment_payload(quota.day)
    second_payload["document_number"] = "B7654321"
    first = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )
    second = agent_client.post("/api/v1/appointments", second_payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 201
    quota.refresh_from_db()
    assert quota.booked_count == 2


@pytest.mark.django_db
def test_create_rejects_missing_or_full_quota(agent_client):
    day = dubai_today()
    ServiceCache.objects.create(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    missing = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(day),
        format="json",
    )
    seed_bookable_quota(capacity=1, booked_count=1)
    full = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(day),
        format="json",
    )

    assert missing.status_code == 400
    assert missing.json()["detail"] == "Quota is not open for this service and day"
    assert full.status_code == 409
    assert full.json()["detail"] == "Quota is full"


@pytest.mark.django_db
def test_create_rejects_past_dubai_date(agent_client):
    quota = seed_bookable_quota()
    response = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day - timedelta(days=1)),
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Appointment date cannot be in the past"


@pytest.mark.django_db
def test_by_token_is_public_and_hides_document_number(agent_client, api_client):
    quota = seed_bookable_quota()
    created = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )
    response = api_client.get(
        f"/api/v1/appointments/by-token/{created.json()['access_token']}"
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Siti Aminah"
    assert "document_number" not in response.json()
    assert response.json()["qr_payload"]


@pytest.mark.django_db
def test_by_token_rejects_unknown_token(api_client):
    response = api_client.get("/api/v1/appointments/by-token/unknown-token")
    assert response.status_code == 404


def test_qr_payload_is_urlsafe_signed_booking_code():
    encoded = make_qr_payload("KJRI-A7F2", "test-secret")
    payload = json.loads(base64.urlsafe_b64decode(encoded))

    assert payload["c"] == "KJRI-A7F2"
    assert len(payload["s"]) == 16


@pytest.mark.django_db
def test_cancel_booked_appointment_decrements_quota(agent_client):
    quota = seed_bookable_quota()
    created = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )
    response = agent_client.post(f"/api/v1/appointments/{created.json()['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    quota.refresh_from_db()
    assert quota.booked_count == 0


@pytest.mark.django_db
def test_cancel_rejects_non_booked_appointment(agent_client):
    quota = seed_bookable_quota()
    created = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )
    first = agent_client.post(f"/api/v1/appointments/{created.json()['id']}/cancel")
    second = agent_client.post(f"/api/v1/appointments/{created.json()['id']}/cancel")

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Only booked appointments can be cancelled"


@pytest.mark.django_db
def test_cancel_by_booking_code(agent_client):
    quota = seed_bookable_quota()
    created = agent_client.post(
        "/api/v1/appointments",
        appointment_payload(quota.day),
        format="json",
    )
    response = agent_client.post(
        "/api/v1/appointments/cancel-by-code",
        {"booking_code": created.json()["booking_code"]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
