from datetime import date, datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import httpx
import pytest

from appointments.models import Appointment, CheckIn
from appointments.qr import make_qr_payload


def dubai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Dubai")).date()


def checkin_payload(booking_code: str = "KJRI-CHECKIN") -> dict[str, str]:
    return {"qr_payload": make_qr_payload(booking_code, "dev-qr-secret")}


@pytest.fixture
def booked_appointment(db):
    return Appointment.objects.create(
        booking_code="KJRI-CHECKIN",
        access_token="test-access-token",
        antrian_service_id=7,
        full_name="Siti Aminah",
        document_number="A1234567",
        appointment_date=dubai_today(),
    )


def _queue_client(monkeypatch) -> Mock:
    client = Mock()
    client.create_queue.return_value = {"id": 91, "queue_number": "PAS-001"}
    monkeypatch.setattr(
        "appointments.services.AntrianClient",
        lambda: client,
    )
    return client


@pytest.mark.django_db
def test_checkin_creates_antrian_queue_and_records_checkin(
    staff_client, staff_user, booked_appointment, monkeypatch
):
    antrian_client = _queue_client(monkeypatch)
    response = staff_client.post("/api/v1/check-in", checkin_payload(), format="json")

    assert response.status_code == 200
    assert response.json() == {
        "booking_code": "KJRI-CHECKIN",
        "antrian_service_id": 7,
        "full_name": "Siti Aminah",
        "appointment_date": dubai_today().isoformat(),
        "status": "checked_in",
        "queue_number": "PAS-001",
    }
    antrian_client.create_queue.assert_called_once_with(7, "KJRI-CHECKIN")
    booked_appointment.refresh_from_db()
    assert booked_appointment.antrian_queue_id == 91
    assert booked_appointment.status == Appointment.Status.CHECKED_IN
    check_in = CheckIn.objects.get()
    assert check_in.staff_user_id == staff_user.id


@pytest.mark.django_db
def test_checkin_antrian_failure_keeps_appointment_booked(
    staff_client, booked_appointment, monkeypatch
):
    request = httpx.Request("POST", "http://antrian/internal/queue/")
    response = httpx.Response(500, request=request)
    client = Mock()
    client.create_queue.side_effect = httpx.HTTPStatusError(
        "Antrian failed", request=request, response=response
    )
    monkeypatch.setattr("appointments.services.AntrianClient", lambda: client)

    response = staff_client.post("/api/v1/check-in", checkin_payload(), format="json")

    assert response.status_code == 502
    booked_appointment.refresh_from_db()
    assert booked_appointment.status == Appointment.Status.BOOKED
    assert booked_appointment.queue_number is None


@pytest.mark.django_db
def test_checkin_is_idempotent_after_success(
    staff_client, booked_appointment, monkeypatch
):
    antrian_client = _queue_client(monkeypatch)
    first = staff_client.post("/api/v1/check-in", checkin_payload(), format="json")
    second = staff_client.post("/api/v1/check-in", checkin_payload(), format="json")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["queue_number"] == "PAS-001"
    antrian_client.create_queue.assert_called_once()
    assert CheckIn.objects.count() == 1
    booked_appointment.refresh_from_db()
    assert booked_appointment.status == Appointment.Status.CHECKED_IN


@pytest.mark.django_db
def test_checkin_rejects_appointment_on_wrong_day(
    staff_client, booked_appointment, monkeypatch
):
    antrian_client = _queue_client(monkeypatch)
    booked_appointment.appointment_date = dubai_today() + timedelta(days=1)
    booked_appointment.save(update_fields=["appointment_date"])

    response = staff_client.post("/api/v1/check-in", checkin_payload(), format="json")

    assert response.status_code == 409
    assert (
        response.json()["detail"] == "Check-in is only allowed on the appointment date"
    )
    antrian_client.create_queue.assert_not_called()
