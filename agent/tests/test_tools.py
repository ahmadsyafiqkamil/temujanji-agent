import json

import httpx
import pytest
import respx

from agent import tools


@pytest.fixture(autouse=True)
def api_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEMUJANJI_API_BASE", "https://temujanji.test/api/v1")
    monkeypatch.setenv("AGENT_API_KEY", "test-agent-key")
    tools.set_telegram_user_id(None)


@pytest.mark.asyncio
@respx.mock
async def test_list_services_sends_agent_key():
    route = respx.get("https://temujanji.test/api/v1/services").mock(
        return_value=httpx.Response(
            200, json=[{"antrian_service_id": 7, "name": "Paspor"}]
        )
    )

    result = await tools.list_services()

    assert result == [{"antrian_service_id": 7, "name": "Paspor"}]
    assert route.calls.last.request.headers["X-API-Key"] == "test-agent-key"


@pytest.mark.asyncio
@respx.mock
async def test_get_availability_sends_date_range():
    route = respx.get(
        "https://temujanji.test/api/v1/availability",
        params={"service_id": "7", "from": "2026-08-10", "to": "2026-08-11"},
    ).mock(return_value=httpx.Response(200, json={"availability": []}))

    result = await tools.get_availability(7, "2026-08-10", "2026-08-11")

    assert result == {"availability": []}
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_create_appointment_binds_telegram_sender():
    route = respx.post("https://temujanji.test/api/v1/appointments").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "00000000-0000-0000-0000-000000000001",
                "booking_code": "KJRI-ABC12345",
                "magic_url": "https://web.test/j/token",
            },
        )
    )
    tools.set_telegram_user_id("12345")

    result = await tools.create_appointment(
        7, "Siti Aminah", "A1234567", "2026-08-10"
    )

    assert result["magic_url"] == "https://web.test/j/token"
    assert json.loads(route.calls.last.request.content)["telegram_user_id"] == "12345"


@pytest.mark.asyncio
@respx.mock
async def test_cancel_appointment_uses_booking_code():
    route = respx.post(
        "https://temujanji.test/api/v1/appointments/cancel-by-code"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"booking_code": "KJRI-ABC12345", "status": "cancelled"},
        )
    )

    result = await tools.cancel_appointment("KJRI-ABC12345")

    assert result["status"] == "cancelled"
    assert json.loads(route.calls.last.request.content) == {
        "booking_code": "KJRI-ABC12345"
    }
