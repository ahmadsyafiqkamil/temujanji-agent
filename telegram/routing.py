"""Pure Telegram inbound routing for the two-menu KJRI chatbot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MENU_KONSULER = "Cek layanan kekonsuleran"
MENU_JANJI = "Janji temu"
MENU_KEMBALI = "Kembali ke menu"
MENU_GREETING = (
    "Assalamualaikum / Selamat datang di layanan chatbot KJRI Dubai.\n\n"
    "Pilih menu:"
)

Track = Literal["konsuler", "janji_temu"]
Action = Literal["show_menu", "run_agent"]


@dataclass(frozen=True)
class InboundRoute:
    action: Action
    track: Track | None
    call_agent: bool


def route_inbound_text(text: str, current_track: str | None) -> InboundRoute:
    stripped = text.strip()
    if stripped in {"/start", MENU_KEMBALI}:
        return InboundRoute(action="show_menu", track=None, call_agent=False)
    if stripped == MENU_KONSULER:
        return InboundRoute(action="run_agent", track="konsuler", call_agent=True)
    if stripped == MENU_JANJI:
        return InboundRoute(action="run_agent", track="janji_temu", call_agent=True)
    resolved: Track | None
    if current_track in {"konsuler", "janji_temu"}:
        resolved = current_track  # type: ignore[assignment]
    else:
        resolved = None
    return InboundRoute(action="run_agent", track=resolved, call_agent=True)


def menu_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": MENU_KONSULER}],
            [{"text": MENU_JANJI}],
            [{"text": MENU_KEMBALI}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def should_send_qr(track: str | None, booking: dict[str, str] | None) -> bool:
    return track == "janji_temu" and bool(booking and booking.get("qr_payload"))
