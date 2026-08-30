from datetime import date

import httpx
import pytest
import respx
from django.test import override_settings

from appointments.models import Appointment
from catalog.antrian_client import AntrianClient
from catalog.models import DailyQuota, ServiceCache


@pytest.mark.django_db
def test_admin_can_create_quota_and_availability_returns_remaining(
    admin_client, agent_client
):
    ServiceCache.objects.create(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    create_response = admin_client.post(
        "/api/v1/admin/quotas",
        {"antrian_service_id": 7, "day": "2026-08-10", "capacity": 2},
        format="json",
    )
    availability_response = agent_client.get(
        "/api/v1/availability",
        {"service_id": 7, "from": "2026-08-10", "to": "2026-08-11"},
    )

    assert create_response.status_code == 201
    assert availability_response.status_code == 200
    assert availability_response.json() == {
        "service_id": 7,
        "availability": [{"day": "2026-08-10", "remaining": 2}],
    }


@pytest.mark.django_db
def test_sync_upserts_services_and_lists_only_active_services(
    admin_client, agent_client, monkeypatch
):
    ServiceCache.objects.create(
        antrian_service_id=7,
        code="OLD",
        name="Old name",
        is_active=False,
    )

    def fake_list_services(self):
        return [
            {"id": 7, "code": "PAS", "name": "Paspor", "is_active": True},
            {"id": 8, "code": "VISA", "name": "Visa", "is_active": False},
        ]

    monkeypatch.setattr(AntrianClient, "list_services", fake_list_services)

    sync_response = admin_client.post("/api/v1/services/sync")
    services_response = agent_client.get("/api/v1/services")

    assert sync_response.status_code == 200
    assert sync_response.json() == {"synced": 2}
    assert ServiceCache.objects.get(pk=7).name == "Paspor"
    assert services_response.status_code == 200
    assert services_response.json() == [
        {
            "antrian_service_id": 7,
            "code": "PAS",
            "name": "Paspor",
            "is_active": True,
        }
    ]


@pytest.mark.django_db
def test_rejects_capacity_below_existing_bookings(admin_client):
    ServiceCache.objects.create(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    quota = DailyQuota.objects.create(
        antrian_service_id=7,
        day=date(2026, 8, 10),
        capacity=3,
        booked_count=2,
    )
    response = admin_client.patch(
        f"/api/v1/admin/quotas/{quota.id}",
        {"capacity": 1},
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Capacity cannot be below booked_count"


@pytest.mark.django_db
def test_admin_lists_appointments_with_filters(admin_client):
    booked = Appointment.objects.create(
        booking_code="KJRI-BOOKED",
        access_token="booked-token",
        antrian_service_id=7,
        full_name="Siti Aminah",
        document_number="A1234567",
        appointment_date=date(2026, 8, 10),
        status="booked",
    )
    Appointment.objects.create(
        booking_code="KJRI-CANCELLED",
        access_token="cancelled-token",
        antrian_service_id=8,
        full_name="Ahmad Fauzi",
        document_number="B7654321",
        appointment_date=date(2026, 8, 11),
        status="cancelled",
    )
    filtered = admin_client.get(
        "/api/v1/admin/appointments",
        {"date": "2026-08-10", "service_id": 7, "status": "booked"},
    )

    assert filtered.status_code == 200
    assert filtered.json() == [
        {
            "id": str(booked.id),
            "booking_code": "KJRI-BOOKED",
            "antrian_service_id": 7,
            "full_name": "Siti Aminah",
            "appointment_date": "2026-08-10",
            "status": "booked",
            "qr_payload": filtered.json()[0]["qr_payload"],
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        [{"id": 7, "code": "PAS", "name": "Paspor", "is_active": True}],
        {
            "services": [
                {"id": 7, "code": "PAS", "name": "Paspor", "is_active": True}
            ]
        },
    ],
)
def test_antrian_client_accepts_list_and_wrapped_service_responses(payload):
    with (
        override_settings(ANTRIAN_BASE_URL="https://antrian.example/api"),
        respx.mock(assert_all_called=True) as router,
    ):
        router.get("https://antrian.example/api/public/services/").mock(
            return_value=httpx.Response(200, json=payload)
        )
        client = AntrianClient(base_url="https://antrian.example/api")
        assert client.list_services() == [
            {"id": 7, "code": "PAS", "name": "Paspor", "is_active": True}
        ]
