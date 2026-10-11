"""Pure Telegram inbound routing for the language-gated KJRI chatbot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Never

from telegram.i18n import (
    LANGUAGE_LABELS,
    Locale,
    locale_from_language_label,
    locale_from_menu_label,
    menu_action_from_label,
    parse_locale,
    t,
)

Track = Literal["konsuler", "janji_temu"]
Action = Literal["show_language", "show_menu", "run_agent"]


@dataclass(frozen=True)
class InboundRoute:
    action: Action
    track: Track | None
    locale: Locale | None
    call_agent: bool


def route_inbound_text(
    text: str,
    current_track: str | None,
    current_locale: str | None = None,
) -> InboundRoute:
    stripped = text.strip()
    locale = parse_locale(current_locale)

    if (
        stripped == "/start"
        or stripped.startswith("/start ")
        or stripped.startswith("/start@")
    ):
        return InboundRoute(
            action="show_language", track=None, locale=None, call_agent=False
        )

    language = locale_from_language_label(stripped)
    if language is not None:
        return InboundRoute(
            action="show_menu", track=None, locale=language, call_agent=False
        )

    menu_action = menu_action_from_label(stripped)
    if menu_action == "kembali":
        if locale is not None:
            return InboundRoute(
                action="show_menu", track=None, locale=None, call_agent=False
            )
        return InboundRoute(
            action="show_language", track=None, locale=None, call_agent=False
        )

    if menu_action == "konsuler":
        inferred = locale or locale_from_menu_label(stripped)
        return InboundRoute(
            action="run_agent",
            track="konsuler",
            locale=inferred if locale is None else None,
            call_agent=True,
        )
    if menu_action == "janji_temu":
        inferred = locale or locale_from_menu_label(stripped)
        return InboundRoute(
            action="run_agent",
            track="janji_temu",
            locale=inferred if locale is None else None,
            call_agent=True,
        )
    if menu_action is not None:
        unreachable: Never = menu_action
        raise ValueError(f"unhandled menu action: {unreachable}")

    if locale is None:
        return InboundRoute(
            action="show_language", track=None, locale=None, call_agent=False
        )

    resolved: Track | None
    if current_track in {"konsuler", "janji_temu"}:
        resolved = current_track
    else:
        resolved = None
    return InboundRoute(
        action="run_agent", track=resolved, locale=None, call_agent=True
    )


def _one_time_keyboard(rows: list[list[dict[str, str]]]) -> dict[str, Any]:
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": True,
        "is_persistent": False,
    }


def language_keyboard() -> dict[str, Any]:
    return _one_time_keyboard(
        [
            [{"text": LANGUAGE_LABELS["id"]}],
            [{"text": LANGUAGE_LABELS["en"]}],
            [{"text": LANGUAGE_LABELS["ar"]}],
        ]
    )


def menu_keyboard(locale: str | None) -> dict[str, Any]:
    resolved = parse_locale(locale) or "id"
    return _one_time_keyboard(
        [
            [{"text": t(resolved, "menu_konsuler")}],
            [{"text": t(resolved, "menu_janji")}],
            [{"text": t(resolved, "menu_kembali")}],
        ]
    )


def remove_keyboard() -> dict[str, Any]:
    return {"remove_keyboard": True}


def should_send_qr(track: str | None, booking: dict[str, str] | None) -> bool:
    return track == "janji_temu" and bool(booking and booking.get("qr_payload"))
