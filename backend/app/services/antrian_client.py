from typing import Any

import httpx

from backend.app.config import settings


class AntrianClient:
    def __init__(
        self,
        base_url: str = settings.antrian_base_url,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def list_services(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            transport=self.transport,
            timeout=10.0,
        ) as client:
            response = await client.get("/public/services/")
            response.raise_for_status()

        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("services"), list):
            return payload["services"]
        raise ValueError("Antrian services response has an invalid shape")
