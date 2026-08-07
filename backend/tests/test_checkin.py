from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db import get_session
from backend.app.deps import require_staff
from backend.app.main import app
from backend.app.models import (
    Appointment,
    AppointmentStatus,
    CheckIn,
    StaffRole,
    StaffUser,
)
from backend.app.routers.checkin import get_antrian_client
from backend.app.services.qr import make_qr_payload


class FakeResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def first(self) -> object | None:
        return self.values[0] if self.values else None


class FakeSession:
    def __init__(self, appointment: Appointment) -> None:
        self.appointment = appointment
        self.check_ins: list[CheckIn] = []

    async def exec(self, statement: object) -> FakeResult:
        parameters = statement.compile().params
        if parameters.get("booking_code_1") == self.appointment.booking_code:
            return FakeResult([self.appointment])
        return FakeResult([])

    def add(self, value: object) -> None:
        if isinstance(value, CheckIn):
            self.check_ins.append(value)

    async def commit(self) -> None:
        return None

    async def refresh(self, _: object) -> None:
        return None


def dubai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Dubai")).date()


@pytest.fixture
def checkin_api():
    appointment = Appointment(
        booking_code="KJRI-CHECKIN",
        access_token="test-access-token",
        antrian_service_id=7,
        full_name="Siti Aminah",
        document_number="A1234567",
        appointment_date=dubai_today(),
    )
    session = FakeSession(appointment)
    staff_user = StaffUser(
        id=11,
        username="staff",
        password_hash="unused",
        role=StaffRole.STAFF,
    )
    antrian_client = AsyncMock()
    antrian_client.create_queue.return_value = {"id": 91, "queue_number": "PAS-001"}

    async def override_session():
        yield session

    async def override_staff() -> StaffUser:
        return staff_user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_staff] = override_staff
    app.dependency_overrides[get_antrian_client] = lambda: antrian_client
    yield session, appointment, antrian_client
    app.dependency_overrides.clear()


def checkin_payload(booking_code: str = "KJRI-CHECKIN") -> dict[str, str]:
    return {"qr_payload": make_qr_payload(booking_code, "dev-qr-secret")}


@pytest.mark.asyncio
async def test_checkin_creates_antrian_queue_and_records_checkin(checkin_api):
    session, appointment, antrian_client = checkin_api
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/check-in", json=checkin_payload())

    assert response.status_code == 200
    assert response.json() == {
        "booking_code": "KJRI-CHECKIN",
        "antrian_service_id": 7,
        "full_name": "Siti Aminah",
        "appointment_date": dubai_today().isoformat(),
        "status": "checked_in",
        "queue_number": "PAS-001",
    }
    antrian_client.create_queue.assert_awaited_once_with(7, "KJRI-CHECKIN")
    assert appointment.antrian_queue_id == 91
    assert appointment.status is AppointmentStatus.CHECKED_IN
    assert len(session.check_ins) == 1
    assert session.check_ins[0].staff_user_id == 11


@pytest.mark.asyncio
async def test_checkin_antrian_failure_keeps_appointment_booked(checkin_api):
    _, appointment, antrian_client = checkin_api
    request = httpx.Request("POST", "http://antrian/internal/queue/")
    response = httpx.Response(500, request=request)
    antrian_client.create_queue.side_effect = httpx.HTTPStatusError(
        "Antrian failed", request=request, response=response
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/check-in", json=checkin_payload())

    assert response.status_code == 502
    assert appointment.status is AppointmentStatus.BOOKED
    assert appointment.queue_number is None


@pytest.mark.asyncio
async def test_checkin_is_idempotent_after_success(checkin_api):
    session, appointment, antrian_client = checkin_api
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/check-in", json=checkin_payload())
        second = await client.post("/api/v1/check-in", json=checkin_payload())

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["queue_number"] == "PAS-001"
    antrian_client.create_queue.assert_awaited_once()
    assert len(session.check_ins) == 1
    assert appointment.status is AppointmentStatus.CHECKED_IN


@pytest.mark.asyncio
async def test_checkin_rejects_appointment_on_wrong_day(checkin_api):
    _, appointment, antrian_client = checkin_api
    appointment.appointment_date = dubai_today() + timedelta(days=1)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/check-in", json=checkin_payload())

    assert response.status_code == 409
    assert (
        response.json()["detail"] == "Check-in is only allowed on the appointment date"
    )
    antrian_client.create_queue.assert_not_awaited()
