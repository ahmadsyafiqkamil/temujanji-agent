"""Temujanji API tools exposed to the booking agent."""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any

import httpx

_telegram_user_id: ContextVar[str | None] = ContextVar(
    "telegram_user_id", default=None
)


def set_telegram_user_id(user_id: str | None) -> None:
    """Bind the authenticated Telegram sender to the current agent invocation."""
    _telegram_user_id.set(user_id)


def _api_base() -> str:
    return os.environ.get("TEMUJANJI_API_BASE", "http://localhost:8000/api/v1").rstrip(
        "/"
    )


def _api_key() -> str:
    return os.environ.get("AGENT_API_KEY", "dev-agent-key")


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, str | int] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(
                method,
                f"{_api_base()}{path}",
                headers={"X-API-Key": _api_key()},
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as error:
        detail = error.response.text
        try:
            detail = error.response.json().get("detail", detail)
        except ValueError:
            pass
        return {"error": str(detail), "status_code": error.response.status_code}
    except httpx.HTTPError:
        return {
            "error": "The appointment service is unreachable. Please try again later.",
            "status_code": 502,
        }


async def list_services() -> dict[str, Any] | list[dict[str, Any]]:
    """List active consular services.

    Each item has antrian_service_id (use this as service_id in other tools),
    code, and name. Menu position is NOT the same as antrian_service_id.
    """
    return await _request("GET", "/services")


async def get_availability(
    service_id: int, from_date: str, to_date: str
) -> dict[str, Any] | list[dict[str, Any]]:
    """Get remaining daily capacity for a service over ISO-8601 dates (YYYY-MM-DD).

    service_id must be antrian_service_id from list_services, never the user's
    menu number.
    """
    return await _request(
        "GET",
        "/availability",
        params={"service_id": service_id, "from": from_date, "to": to_date},
    )


async def create_appointment(
    service_id: int, full_name: str, passport_number: str, appointment_date: str
) -> dict[str, Any] | list[dict[str, Any]]:
    """Create a confirmed appointment after the user has explicitly confirmed all data.

    service_id must be antrian_service_id from list_services, never the user's
    menu number.
    """
    telegram_user_id = _telegram_user_id.get()
    if telegram_user_id is None:
        return {
            "error": "Telegram user identity is unavailable.",
            "status_code": 400,
        }
    return await _request(
        "POST",
        "/appointments",
        json={
            "antrian_service_id": service_id,
            "full_name": full_name,
            "document_number": passport_number,
            "appointment_date": appointment_date,
            "telegram_user_id": telegram_user_id,
        },
    )


async def cancel_appointment(booking_code: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Cancel a booking by its booking code after confirming the user's intent."""
    return await _request(
        "POST",
        "/appointments/cancel-by-code",
        json={"booking_code": booking_code},
    )
