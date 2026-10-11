import pytest
from google.adk.sessions import InMemorySessionService

from telegram.session_state import write_session_state

APP = "temujanji_telegram"


@pytest.mark.asyncio
async def test_mutating_session_copy_does_not_persist_locale():
    service = InMemorySessionService()
    await service.create_session(
        app_name=APP,
        user_id="telegram-1",
        session_id="telegram-1",
        state={"track": None, "locale": None},
    )
    copied = await service.get_session(
        app_name=APP, user_id="telegram-1", session_id="telegram-1"
    )
    assert copied is not None
    copied.state["locale"] = "en"
    copied.state["track"] = "konsuler"
    reloaded = await service.get_session(
        app_name=APP, user_id="telegram-1", session_id="telegram-1"
    )
    assert reloaded is not None
    assert reloaded.state.get("locale") is None
    assert reloaded.state.get("track") is None


@pytest.mark.asyncio
async def test_write_session_state_persists_locale_and_track():
    service = InMemorySessionService()
    session = await service.create_session(
        app_name=APP,
        user_id="telegram-2",
        session_id="telegram-2",
        state={"track": None, "locale": None},
    )
    await write_session_state(service, session, track="konsuler", locale="en")
    reloaded = await service.get_session(
        app_name=APP, user_id="telegram-2", session_id="telegram-2"
    )
    assert reloaded is not None
    assert reloaded.state.get("locale") == "en"
    assert reloaded.state.get("track") == "konsuler"
