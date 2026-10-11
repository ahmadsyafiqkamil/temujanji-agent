"""Persist Telegram routing fields into ADK session storage.

InMemorySessionService.get_session() returns a copy. Mutating session.state
does not write back. State only sticks via create_session() or append_event()
with a state_delta.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session

from telegram.i18n import Locale


def routing_state_delta(
    *, track: str | None, locale: Locale | None
) -> dict[str, Any]:
    return {"track": track, "locale": locale}


async def write_session_state(
    session_service: BaseSessionService,
    session: Session,
    *,
    track: str | None,
    locale: Locale | None,
) -> None:
    event = Event(
        invocation_id=f"telegram-routing-{uuid4()}",
        author="user",
        actions=EventActions(
            state_delta=routing_state_delta(track=track, locale=locale)
        ),
    )
    await session_service.append_event(session=session, event=event)
