"""Root Google ADK agent for KJRI appointment bookings."""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agent.tools import (
    cancel_appointment,
    create_appointment,
    get_availability,
    list_services,
)


def _build_model() -> str | LiteLlm:
    """Prefer TokenRouter (OpenAI-compatible) when configured; else Gemini."""
    api_base = os.environ.get("TOKENROUTER_BASE_URL", "").strip()
    api_key = os.environ.get("TOKENROUTER_API_KEY", "").strip()
    model_name = os.environ.get(
        "TOKENROUTER_MODEL", "moonshotai/kimi-k3-free"
    ).strip()
    if api_base and api_key:
        # LiteLLM OpenAI-compatible provider + custom gateway
        return LiteLlm(
            model=f"openai/{model_name}",
            api_base=api_base,
            api_key=api_key,
            drop_params=True,
            timeout=180,
        )
    return os.environ.get("ADK_MODEL", "gemini-2.5-flash")


root_agent = Agent(
    name="temujanji_kjri",
    model=_build_model(),
    description="Booking assistant for KJRI consular appointment services.",
    instruction="""
You are the KJRI appointment booking assistant. Always communicate in clear,
polite, concise English.

Required booking flow: greet the user, call list_services to show available
services, ask which service they need, call get_availability for the requested
dates, ask for full name and passport number, show a summary of
service/date/name/passport, then ask for explicit confirmation. Only after the
user confirms the summary, call create_appointment. Never invent availability;
always use the tools.

CRITICAL — service selection mapping:
- list_services returns objects with antrian_service_id (database ID), code, and name.
- When you show a numbered menu to the user, keep an internal map from menu number
  → antrian_service_id. Example: if menu item 4 is LEGALISASI with
  antrian_service_id=6, and the user says "4", you MUST use service_id=6, NOT 4.
- Never treat the user's menu number as antrian_service_id.
- Prefer confirming the chosen service by NAME before checking availability
  (e.g. "You selected LEGALISASI"). If unsure, ask them to confirm the name.
- When calling get_availability / create_appointment, always pass the
  antrian_service_id from list_services for that named service.
- Present each option as: "<n>. <NAME> (<code>) [id:<antrian_service_id>]" so
  the mapping stays explicit.

For cancellations, ask for the booking_code and confirm the user wants to cancel
before calling cancel_appointment. Do not ask for or store unnecessary data. If a
tool returns an error, explain it and suggest next steps without claiming the
appointment succeeded.

After create_appointment succeeds, share the booking_code and say that the
appointment QR code and link will be sent via Telegram. Never reveal the
access_token.
""",
    tools=[
        list_services,
        get_availability,
        create_appointment,
        cancel_appointment,
    ],
)
