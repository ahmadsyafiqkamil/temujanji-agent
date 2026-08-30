from typing import Any

import httpx
from django.conf import settings


class AntrianClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ANTRIAN_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.ANTRIAN_API_KEY

    def list_services(self) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.base_url}/public/services/",
            headers={"X-API-Key": self.api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("services"), list):
            return payload["services"]
        raise ValueError("Antrian returned an invalid service list")

    def create_queue(self, service_id: int, booking_code: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/internal/queue/",
            json={"service_id": service_id, "booking_code": booking_code},
            headers={"X-API-Key": self.api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Antrian returned an invalid queue")
        return payload
