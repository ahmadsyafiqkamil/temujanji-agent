from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient, MockTransport, Request, Response

from backend.app.db import get_session
from backend.app.deps import require_admin, require_agent_api_key
from backend.app.main import app
from backend.app.models import (
    Appointment,
    AppointmentStatus,
    DailyQuota,
    ServiceCache,
    StaffRole,
    StaffUser,
)
from backend.app.services.antrian_client import AntrianClient


class FakeResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values

    def first(self) -> object | None:
        return self.values[0] if self.values else None


class FakeSession:
    def __init__(self) -> None:
        self.services: dict[int, ServiceCache] = {}
        self.quotas: dict[int, DailyQuota] = {}
        self.appointments: dict[object, Appointment] = {}
        self.next_quota_id = 1

    async def get(self, model: type[object], identifier: int) -> object | None:
        if model is ServiceCache:
            return self.services.get(identifier)
        if model is DailyQuota:
            return self.quotas.get(identifier)
        if model is Appointment:
            return self.appointments.get(identifier)
        return None

    async def exec(self, statement: object) -> FakeResult:
        entity = statement.column_descriptions[0]["entity"]
        if entity is ServiceCache:
            services = list(self.services.values())
            if "is_active" in str(statement):
                services = [service for service in services if service.is_active]
            return FakeResult(services)
        if entity is DailyQuota:
            return FakeResult(list(self.quotas.values()))
        if entity is Appointment:
            appointments = list(self.appointments.values())
            parameters = statement.compile().params
            for parameter_name, attribute_name in (
                ("appointment_date_1", "appointment_date"),
                ("antrian_service_id_1", "antrian_service_id"),
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
        if isinstance(value, ServiceCache):
            self.services[value.antrian_service_id] = value
        if isinstance(value, DailyQuota):
            if value.id is None:
                value.id = self.next_quota_id
                self.next_quota_id += 1
            self.quotas[value.id] = value
        if isinstance(value, Appointment):
            self.appointments[value.id] = value

    async def delete(self, quota: DailyQuota) -> None:
        assert quota.id is not None
        del self.quotas[quota.id]

    async def commit(self) -> None:
        return None

    async def refresh(self, _: object) -> None:
        return None


class FakeAntrianClient:
    async def list_services(self) -> list[dict[str, object]]:
        return [
            {"id": 7, "code": "PAS", "name": "Paspor", "is_active": True},
            {"id": 8, "code": "VISA", "name": "Visa", "is_active": False},
        ]


@pytest.fixture
def api_client():
    session = FakeSession()

    async def override_admin() -> StaffUser:
        return StaffUser(
            id=1,
            username="admin",
            password_hash="unused",
            role=StaffRole.ADMIN,
        )

    async def override_agent_key() -> None:
        return None

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[require_admin] = override_admin
    app.dependency_overrides[require_agent_api_key] = override_agent_key

    yield session
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_can_create_quota_and_availability_returns_remaining(api_client):
    api_client.services[7] = ServiceCache(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/admin/quotas",
            json={"antrian_service_id": 7, "day": "2026-08-10", "capacity": 2},
        )
        availability_response = await client.get(
            "/api/v1/availability",
            params={
                "service_id": 7,
                "from": "2026-08-10",
                "to": "2026-08-11",
            },
        )

    assert create_response.status_code == 201
    assert availability_response.status_code == 200
    assert availability_response.json() == {
        "service_id": 7,
        "availability": [{"day": "2026-08-10", "remaining": 2}],
    }


@pytest.mark.asyncio
async def test_sync_upserts_services_and_lists_only_active_services(api_client):
    from backend.app.routers.services import get_antrian_client

    api_client.services[7] = ServiceCache(
        antrian_service_id=7,
        code="OLD",
        name="Old name",
        is_active=False,
    )
    app.dependency_overrides[get_antrian_client] = FakeAntrianClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sync_response = await client.post("/api/v1/services/sync")
        services_response = await client.get("/api/v1/services")

    assert sync_response.status_code == 200
    assert sync_response.json() == {"synced": 2}
    assert api_client.services[7].name == "Paspor"
    assert services_response.status_code == 200
    assert services_response.json() == [
        {
            "antrian_service_id": 7,
            "code": "PAS",
            "name": "Paspor",
            "is_active": True,
        }
    ]


@pytest.mark.asyncio
async def test_rejects_capacity_below_existing_bookings(api_client):
    api_client.services[7] = ServiceCache(
        antrian_service_id=7,
        code="PAS",
        name="Paspor",
        is_active=True,
    )
    api_client.quotas[1] = DailyQuota(
        id=1,
        antrian_service_id=7,
        day=date(2026, 8, 10),
        capacity=3,
        booked_count=2,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/api/v1/admin/quotas/1", json={"capacity": 1})

    assert response.status_code == 409
    assert response.json()["detail"] == "Capacity cannot be below booked_count"


@pytest.mark.asyncio
async def test_admin_lists_appointments_with_filters(api_client):
    booked = Appointment(
        booking_code="KJRI-BOOKED",
        access_token="booked-token",
        antrian_service_id=7,
        full_name="Siti Aminah",
        document_number="A1234567",
        appointment_date=date(2026, 8, 10),
    )
    cancelled = Appointment(
        booking_code="KJRI-CANCELLED",
        access_token="cancelled-token",
        antrian_service_id=8,
        full_name="Ahmad Fauzi",
        document_number="B7654321",
        appointment_date=date(2026, 8, 11),
        status=AppointmentStatus.CANCELLED,
    )
    api_client.add(booked)
    api_client.add(cancelled)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        filtered = await client.get(
            "/api/v1/admin/appointments",
            params={"date": "2026-08-10", "service_id": 7, "status": "booked"},
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


@pytest.mark.asyncio
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
async def test_antrian_client_accepts_list_and_wrapped_service_responses(payload):
    def handler(request: Request) -> Response:
        assert request.url.path == "/api/public/services/"
        return Response(200, json=payload)

    client = AntrianClient(
        base_url="https://antrian.example/api",
        transport=MockTransport(handler),
    )

    assert await client.list_services() == [
        {"id": 7, "code": "PAS", "name": "Paspor", "is_active": True}
    ]
