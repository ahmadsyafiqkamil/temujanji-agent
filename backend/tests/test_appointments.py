import base64
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db import get_session
from backend.app.deps import require_agent_api_key
from backend.app.main import app
from backend.app.models import (
    Appointment,
    AppointmentStatus,
    DailyQuota,
    ServiceCache,
)
from backend.app.services.qr import make_qr_payload


class FakeResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values

    def first(self) -> object | None:
        return self.values[0] if self.values else None


class FakeSession:
    """In-memory double; it records, but cannot enforce SQL row locks."""

    def __init__(self) -> None:
        self.services: dict[int, ServiceCache] = {}
        self.quotas: dict[int, DailyQuota] = {}
        self.appointments: dict[object, Appointment] = {}
        self.next_quota_id = 1

    async def get(self, model: type[object], identifier: object) -> object | None:
        if model is ServiceCache:
            return self.services.get(identifier)
        if model is DailyQuota:
            return self.quotas.get(identifier)
        if model is Appointment:
            return self.appointments.get(identifier)
        return None

    async def exec(self, statement: object) -> FakeResult:
        entity = statement.column_descriptions[0]["entity"]
        parameters = statement.compile().params
        if entity is DailyQuota:
            quotas = list(self.quotas.values())
            service_id = parameters.get("antrian_service_id_1")
            day = parameters.get("day_1")
            if service_id is not None:
                quotas = [
                    quota
                    for quota in quotas
                    if quota.antrian_service_id == service_id
                ]
            if day is not None:
                quotas = [quota for quota in quotas if quota.day == day]
            return FakeResult(quotas)
        if entity is Appointment:
            appointments = list(self.appointments.values())
            for parameter_name, attribute_name in (
                ("id_1", "id"),
                ("booking_code_1", "booking_code"),
                ("access_token_1", "access_token"),
                ("document_number_1", "document_number"),
                ("antrian_service_id_1", "antrian_service_id"),
                ("appointment_date_1", "appointment_date"),
                ("status_1", "status"),
            ):
                if parameter_name in parameters:
                    appointments = [
                        appointment
                        for appointment in appointments
                        if getattr(appointment, attribute_name)
                        == parameters[parameter_name]
                    ]
            return FakeResult(appointments)
        return FakeResult([])

    def add(self, value: object) -> None:
        if isinstance(value, DailyQuota):
            if value.id is None:
                value.id = self.next_quota_id
                self.next_quota_id += 1
            self.quotas[value.id] = value
        if isinstance(value, Appointment):
            self.appointments[value.id] = value

    async def commit(self) -> None:
        return None

    async def refresh(self, _: object) -> None:
        return None


@pytest.fixture
def api_client():
    session = FakeSession()

    async def override_agent_key() -> None:
        return None

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_agent_api_key] = override_agent_key
    yield session
    app.dependency_overrides.clear()


def dubai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Dubai")).date()


def seed_bookable_quota(session: FakeSession, *, capacity: int = 2) -> date:
    day = dubai_today()
    session.services[7] = ServiceCache(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    session.quotas[1] = DailyQuota(
        id=1,
        antrian_service_id=7,
        day=day,
        capacity=capacity,
    )
    return day


def appointment_payload(day: date) -> dict[str, str | int]:
    return {
        "antrian_service_id": 7,
        "full_name": "Siti Aminah",
        "document_number": "A1234567",
        "appointment_date": day.isoformat(),
        "telegram_user_id": "12345",
    }


@pytest.mark.asyncio
async def test_create_increments_quota_and_returns_magic_url(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/appointments", json=appointment_payload(day))

    assert response.status_code == 201
    body = response.json()
    assert body["booking_code"].startswith("KJRI-")
    assert body["magic_url"] == f"http://localhost:3000/j/{body['access_token']}"
    assert api_client.quotas[1].booked_count == 1


@pytest.mark.asyncio
async def test_create_rejects_duplicate_active_booking(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/appointments", json=appointment_payload(day))
        second = await client.post("/api/v1/appointments", json=appointment_payload(day))

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Active appointment already exists"
    assert api_client.quotas[1].booked_count == 1


@pytest.mark.asyncio
async def test_create_allows_different_document_on_same_service_and_day(api_client):
    day = seed_bookable_quota(api_client)
    second_payload = appointment_payload(day)
    second_payload["document_number"] = "B7654321"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/appointments", json=appointment_payload(day))
        second = await client.post("/api/v1/appointments", json=second_payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert api_client.quotas[1].booked_count == 2


@pytest.mark.asyncio
async def test_create_rejects_missing_or_full_quota(api_client):
    day = dubai_today()
    api_client.services[7] = ServiceCache(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.post("/api/v1/appointments", json=appointment_payload(day))
        seed_bookable_quota(api_client, capacity=1)
        api_client.quotas[1].booked_count = 1
        full = await client.post("/api/v1/appointments", json=appointment_payload(day))

    assert missing.status_code == 400
    assert missing.json()["detail"] == "Quota is not open for this service and day"
    assert full.status_code == 409
    assert full.json()["detail"] == "Quota is full"


@pytest.mark.asyncio
async def test_create_rejects_past_dubai_date(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/appointments",
            json=appointment_payload(day - timedelta(days=1)),
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Appointment date cannot be in the past"


@pytest.mark.asyncio
async def test_by_token_is_public_and_hides_document_number(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/appointments", json=appointment_payload(day))
        response = await client.get(
            f"/api/v1/appointments/by-token/{created.json()['access_token']}"
        )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Siti Aminah"
    assert "document_number" not in response.json()
    assert response.json()["qr_payload"]


@pytest.mark.asyncio
async def test_by_token_rejects_unknown_token(api_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/appointments/by-token/unknown-token")

    assert response.status_code == 404


def test_qr_payload_is_urlsafe_signed_booking_code():
    encoded = make_qr_payload("KJRI-A7F2", "test-secret")
    payload = json.loads(base64.urlsafe_b64decode(encoded))

    assert payload["c"] == "KJRI-A7F2"
    assert len(payload["s"]) == 16


@pytest.mark.asyncio
async def test_cancel_booked_appointment_decrements_quota(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/appointments", json=appointment_payload(day))
        response = await client.post(
            f"/api/v1/appointments/{created.json()['id']}/cancel"
        )

    assert response.status_code == 200
    assert response.json()["status"] == AppointmentStatus.CANCELLED.value
    assert api_client.quotas[1].booked_count == 0


@pytest.mark.asyncio
async def test_cancel_rejects_non_booked_appointment(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/appointments", json=appointment_payload(day))
        first = await client.post(f"/api/v1/appointments/{created.json()['id']}/cancel")
        second = await client.post(f"/api/v1/appointments/{created.json()['id']}/cancel")

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Only booked appointments can be cancelled"


@pytest.mark.asyncio
async def test_cancel_by_booking_code(api_client):
    day = seed_bookable_quota(api_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/appointments", json=appointment_payload(day))
        response = await client.post(
            "/api/v1/appointments/cancel-by-code",
            json={"booking_code": created.json()["booking_code"]},
        )

    assert response.status_code == 200
    assert response.json()["status"] == AppointmentStatus.CANCELLED.value
