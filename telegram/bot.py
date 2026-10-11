"""Telegram webhook adapter for the KJRI appointment agent."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Never

import httpx
import qrcode
from fastapi import FastAPI, Header, HTTPException, Request, status
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agent import root_agent
from agent.konsuler.tools import set_channel
from agent.tools import set_telegram_user_id
from telegram.conversation_archive import (
    detect_gratitude_closure,
    save_conversation_archive,
)
from telegram.handoff import (
    can_create_bot_failure_handoff,
    check_and_resolve_timed_out_handoffs,
    detect_escalation_trigger,
    forward_user_message_to_staff,
    get_latest_pengguna_for_session,
    get_user_chat_id_by_session,
    handle_staff_reply,
    has_active_handoff,
    is_from_staff_group,
    resolve_handoff_by_session,
    save_handoff_to_db,
    send_staff_notification,
    set_handoff_in_progress_by_session,
    update_handoff_activity,
)
from telegram.i18n import LANGUAGE_PROMPT, Locale, parse_locale, t
from telegram.markdown_converter import md_to_html
from telegram.routing import (
    language_keyboard,
    menu_keyboard,
    remove_keyboard,
    route_inbound_text,
    should_send_qr,
)
from telegram.session_state import routing_state_delta, write_session_state

APP_NAME = "temujanji_telegram"
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
NGROK_API = os.environ.get("NGROK_API", "http://ngrok:4040")
KJRI_STAFF_GROUP_ID = os.environ.get("KJRI_STAFF_TELEGRAM_GROUP_ID", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Jika final response dari ADK hanya whitespace (sering setelah tool calls pada
# model kecil), satu kali kirim pesan tambahan agar model menulis jawaban Markdown
# lengkap sebelum handoff.
_AGENT_EMPTY_REPLY_NUDGE = (
    "[Instruksi sistem untuk asisten KJRI] Respons teks kepada user pada giliran "
    "terakhir kosong atau hanya whitespace. WAJIB kirim sekarang jawaban lengkap "
    "dalam bahasa state.locale: ## Konteks singkat, ## Ringkasan layanan, "
    "## Persyaratan, ## Biaya (AED), ## Langkah berikutnya. Pakai data dari tool "
    "di percakapan ini; jika belum ada data valid, panggil cari_layanan / "
    "get_detail_layanan sesuai kebutuhan lalu tulis jawaban untuk user."
)

# Per-session transcript buffer (for conversation archives)
_transcript_buffers: dict[str, list[dict]] = {}
_transcript_lock = threading.Lock()

session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)


def _telegram_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    return token


def render_qr_png(payload: str) -> bytes:
    """Render a QR code PNG for the signed check-in payload."""
    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def send_telegram_message(
    chat_id: int, text: str, *, reply_markup: dict[str, Any] | None = None
) -> None:
    html_text = md_to_html(text)
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": html_text,
        "parse_mode": "HTML",
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{_telegram_token()}/sendMessage",
            json=payload,
        )
        if response.status_code != 200:
            # Fallback: resend as plain text without formatting
            payload["text"] = text
            payload.pop("parse_mode", None)
            plain = await client.post(
                f"https://api.telegram.org/bot{_telegram_token()}/sendMessage",
                json=payload,
            )
            plain.raise_for_status()
            return
        response.raise_for_status()


async def send_telegram_qr(
    chat_id: int,
    *,
    qr_payload: str,
    booking_code: str,
    magic_url: str,
    locale: Locale | None = None,
) -> None:
    """Send check-in QR image plus caption with booking code and magic link."""
    png = render_qr_png(qr_payload)
    caption = t(locale, "qr_caption", code=booking_code, url=magic_url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{_telegram_token()}/sendPhoto",
            data={"chat_id": str(chat_id), "caption": caption},
            files={"photo": ("checkin-qr.png", png, "image/png")},
        )
        response.raise_for_status()


def _append_turn(session_id: str, role: str, text: str) -> None:
    """Append one turn to the session transcript buffer (thread-safe)."""
    turn = {
        "role": role,
        "text": text,
        "at": datetime.now(UTC).isoformat(),
    }
    with _transcript_lock:
        if session_id not in _transcript_buffers:
            _transcript_buffers[session_id] = []
        _transcript_buffers[session_id].append(turn)


def _get_and_clear_buffer(session_id: str) -> list[dict]:
    """Return current buffer for session_id and clear it (thread-safe)."""
    with _transcript_lock:
        turns = list(_transcript_buffers.pop(session_id, []))
    return turns


def _staff_display_name_and_pengguna(
    session_id: str,
    message: dict,
) -> tuple[str | None, str]:
    """Return (pengguna_id, display_name) for staff notifications.

    Priority:
    1. nama_lengkap from konsuler.pengguna (keyed by session_id)
    2. first_name + last_name from Telegram message['from']
    3. str(chat_id)
    """
    pengguna_id, nama_lengkap = get_latest_pengguna_for_session(session_id)
    if nama_lengkap:
        return (pengguna_id, nama_lengkap)

    from_data = message.get("from", {})
    parts = []
    if from_data.get("first_name"):
        parts.append(from_data["first_name"])
    if from_data.get("last_name"):
        parts.append(from_data["last_name"])
    if parts:
        return (None, " ".join(parts))

    return (None, str(message["chat"]["id"]))


async def _trigger_bot_failure_handoff(
    chat_id: int,
    session_id: str,
    user_text: str,
    message: dict,
    locale: Locale | None = None,
) -> None:
    """Escalate to human staff when the bot fails to produce a response."""
    if has_active_handoff(session_id):
        await send_telegram_message(
            chat_id,
            t(locale, "handoff_queued"),
        )
        return

    if not can_create_bot_failure_handoff(session_id):
        await send_telegram_message(
            chat_id,
            t(locale, "bot_failure_cooldown"),
        )
        return

    pengguna_id, display_name = _staff_display_name_and_pengguna(session_id, message)

    try:
        save_handoff_to_db(
            session_id=session_id,
            user_chat_id=chat_id,
            pengguna_id=pengguna_id,
            nama_user=display_name,
            pertanyaan_terakhir=user_text,
            layanan_dicari=None,
        )
        if KJRI_STAFF_GROUP_ID:
            await send_staff_notification(
                bot_token=_telegram_token(),
                staff_group_id=KJRI_STAFF_GROUP_ID,
                handoff_id="",
                session_id=session_id,
                nama_user=display_name,
                pertanyaan_terakhir=f"[BOT FAILURE] {user_text}",
            )
        else:
            logger.warning(
                "KJRI_STAFF_TELEGRAM_GROUP_ID not set; skipping staff notification for bot failure"
            )
    except Exception:
        logger.exception(
            "Bot-failure handoff save/notify failed for chat_id=%s session=%s",
            chat_id,
            session_id,
        )
    await send_telegram_message(chat_id, t(locale, "handoff_confirmation"))


async def run_agent(
    user_id: int,
    chat_id: int,
    text: str,
    *,
    track: str | None = None,
    locale: Locale | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Run one message through ADK; return text replies and booking payloads."""
    session_id = f"telegram-{chat_id}"
    adk_user_id = f"telegram-{user_id}"
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=adk_user_id,
        session_id=session_id,
    )
    state = routing_state_delta(track=track, locale=locale)
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=adk_user_id,
            session_id=session_id,
            state=state,
        )

    set_telegram_user_id(str(user_id))
    set_channel("telegram")
    replies: list[str] = []
    bookings: list[dict[str, str]] = []
    logger.info("run_agent start: chat=%s track=%s locale=%s text=%r", chat_id, track, locale, text[:80])
    message = types.Content(role="user", parts=[types.Part.from_text(text=text)])
    async for event in runner.run_async(
        user_id=adk_user_id,
        session_id=session_id,
        new_message=message,
        state_delta=state,
    ):
        for function_response in event.get_function_responses():
            response = function_response.response or {}
            magic_url = response.get("magic_url")
            qr_payload = response.get("qr_payload")
            booking_code = response.get("booking_code")
            if (
                isinstance(magic_url, str)
                and isinstance(qr_payload, str)
                and isinstance(booking_code, str)
            ):
                bookings.append(
                    {
                        "magic_url": magic_url,
                        "qr_payload": qr_payload,
                        "booking_code": booking_code,
                    }
                )
            elif isinstance(magic_url, str):
                # Fallback if older API response without qr_payload
                bookings.append(
                    {
                        "magic_url": magic_url,
                        "qr_payload": "",
                        "booking_code": str(booking_code or "appointment"),
                    }
                )
        if event.is_final_response() and event.content:
            for part in event.content.parts or []:
                if part.text:
                    replies.append(part.text)
    logger.info(
        "run_agent done: chat=%s replies=%d bookings=%d",
        chat_id,
        len(replies),
        len(bookings),
    )
    return replies, bookings


async def _handle_staff_command(chat_id: int, text: str) -> None:
    """Handle /reply and /resolve commands from the staff group only."""
    if not is_from_staff_group(str(chat_id), KJRI_STAFF_GROUP_ID):
        logger.warning("Staff command from non-staff chat_id=%s, ignoring", chat_id)
        return

    if text.startswith("/reply"):
        parts = text[len("/reply "):].split(" ", 1) if text.startswith("/reply ") else []
        if len(parts) < 2:
            await send_telegram_message(
                chat_id, "Format: /reply &lt;session_id&gt; &lt;pesan&gt;"
            )
            return
        target_session_id, pesan_staf = parts[0], parts[1]
        target_chat_id = get_user_chat_id_by_session(target_session_id)
        if target_chat_id is None:
            await send_telegram_message(
                chat_id, f"Session <code>{target_session_id}</code> tidak ditemukan."
            )
            return
        set_handoff_in_progress_by_session(target_session_id)
        logger.info(
            "Webhook: /reply to session=%s chat_id=%s", target_session_id, target_chat_id
        )
        try:
            await handle_staff_reply(
                bot_token=_telegram_token(),
                user_chat_id=target_chat_id,
                pesan_staf=pesan_staf,
            )
        except Exception:
            logger.exception("Failed to forward staff reply for session=%s", target_session_id)

    elif text.startswith("/resolve"):
        target_session_id = text[len("/resolve"):].strip()
        target_chat_id = get_user_chat_id_by_session(target_session_id)
        logger.info("Webhook: /resolve session=%s", target_session_id)
        resolved = resolve_handoff_by_session(target_session_id)
        if resolved:
            logger.info("Webhook: handoff resolved for session=%s", target_session_id)
            if target_chat_id:
                try:
                    await handle_staff_reply(
                        bot_token=_telegram_token(),
                        user_chat_id=target_chat_id,
                        pesan_staf=(
                            "Sesi Anda dengan petugas KJRI telah selesai. "
                            "Anda dapat melanjutkan percakapan dengan bot kami."
                        ),
                    )
                except Exception:
                    logger.exception("Failed to notify user on resolve for session=%s", target_session_id)
            await send_telegram_message(
                chat_id,
                f"Sesi <code>{target_session_id}</code> berhasil di-resolve. Bot aktif kembali untuk user.",
            )
        else:
            logger.warning("Webhook: no active handoff found for session=%s", target_session_id)
            await send_telegram_message(
                chat_id,
                f"Tidak ada handoff aktif untuk sesi <code>{target_session_id}</code>.",
            )


async def handle_inbound(
    chat_id: int,
    text: str,
    user_id: int,
    *,
    sender: dict | None = None,
) -> None:
    session_id = f"telegram-{chat_id}"
    adk_user_id = f"telegram-{user_id}"
    message = {"from": sender or {}, "chat": {"id": chat_id}}

    # ------------------------------------------------------------------
    # Staff commands — only accepted from KJRI_STAFF_GROUP_ID
    # ------------------------------------------------------------------
    if text.startswith(("/reply", "/resolve")):
        await _handle_staff_command(chat_id, text)
        return

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=adk_user_id,
        session_id=session_id,
    )
    current_track = None
    current_locale = None
    if session is not None:
        current_track = session.state.get("track")
        current_locale = parse_locale(session.state.get("locale"))
    route = route_inbound_text(text, current_track, current_locale)
    logger.info("route: chat=%s action=%s track=%s", chat_id, route.action, route.track)
    effective_locale = route.locale if route.locale is not None else current_locale
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=adk_user_id,
            session_id=session_id,
            state=routing_state_delta(
                track=route.track, locale=effective_locale
            ),
        )
    else:
        await write_session_state(
            session_service,
            session,
            track=route.track,
            locale=effective_locale,
        )

    if route.action == "show_language":
        await send_telegram_message(
            chat_id, LANGUAGE_PROMPT, reply_markup=language_keyboard()
        )
        return
    if route.action == "show_menu":
        menu_locale = effective_locale or "id"
        await send_telegram_message(
            chat_id,
            t(menu_locale, "greeting"),
            reply_markup=menu_keyboard(menu_locale),
        )
        return
    if route.action == "run_agent":
        eff_track = route.track if route.track is not None else current_track

        if eff_track == "konsuler":
            # Guard: session already in handoff queue — forward ke staf, bot diam
            if has_active_handoff(session_id):
                update_handoff_activity(session_id)
                if KJRI_STAFF_GROUP_ID:
                    _, display_name = _staff_display_name_and_pengguna(session_id, message)
                    try:
                        await forward_user_message_to_staff(
                            bot_token=_telegram_token(),
                            staff_group_id=KJRI_STAFF_GROUP_ID,
                            session_id=session_id,
                            nama_user=display_name,
                            pesan_user=text,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to forward user message to staff for session=%s",
                            session_id,
                        )
                return

            # Escalation trigger detection — intercept before agent
            if detect_escalation_trigger(text):
                pengguna_id, display_name = _staff_display_name_and_pengguna(session_id, message)
                try:
                    save_handoff_to_db(
                        session_id=session_id,
                        user_chat_id=chat_id,
                        pengguna_id=pengguna_id,
                        nama_user=display_name,
                        pertanyaan_terakhir=text,
                        layanan_dicari=None,
                    )
                    if KJRI_STAFF_GROUP_ID:
                        await send_staff_notification(
                            bot_token=_telegram_token(),
                            staff_group_id=KJRI_STAFF_GROUP_ID,
                            handoff_id="",
                            session_id=session_id,
                            nama_user=display_name,
                            pertanyaan_terakhir=text,
                        )
                    else:
                        logger.warning(
                            "KJRI_STAFF_TELEGRAM_GROUP_ID not set; skipping staff notification"
                        )
                except Exception:
                    logger.exception("Handoff save/notify failed for chat_id=%s", chat_id)
                await send_telegram_message(chat_id, t(effective_locale, "handoff_confirmation"))
                return

            # Closure detection — archive transcript if user says goodbye/thank you
            closure_reason = detect_gratitude_closure(text)
            if closure_reason:
                closure_reply = t(effective_locale, "closure_reply")
                _append_turn(session_id, "user", text)
                _append_turn(session_id, "assistant", closure_reply)
                turns = _get_and_clear_buffer(session_id)
                pengguna_id, _ = get_latest_pengguna_for_session(session_id)
                save_conversation_archive(
                    session_id=session_id,
                    channel="telegram",
                    on=closure_reason,
                    transcript_messages=turns,
                    pengguna_id=pengguna_id,
                )
                await send_telegram_message(chat_id, closure_reply)
                return

            # Append user message to transcript buffer
            _append_turn(session_id, "user", text)

        try:
            replies, bookings = await run_agent(
                user_id,
                chat_id,
                text,
                track=route.track,
                locale=effective_locale,
            )
            if not replies and eff_track == "konsuler":
                logger.warning(
                    "Empty visible response after first agent pass session=%s — retry with nudge",
                    session_id,
                )
                nudge_replies, nudge_bookings = await run_agent(
                    user_id,
                    chat_id,
                    _AGENT_EMPTY_REPLY_NUDGE,
                    track=route.track,
                    locale=effective_locale,
                )
                replies = nudge_replies
                bookings = bookings + nudge_bookings
        except Exception:
            logger.exception("Error running agent for chat_id=%s session=%s", chat_id, session_id)
            if eff_track == "konsuler":
                await _trigger_bot_failure_handoff(chat_id, session_id, text, message, effective_locale)
                return
            raise

        hidden = remove_keyboard()
        if replies:
            for reply in replies:
                await send_telegram_message(chat_id, reply, reply_markup=hidden)
            if eff_track == "konsuler":
                _append_turn(session_id, "assistant", "\n".join(replies))
        else:
            logger.warning(
                "Agent produced no text response for session=%s — triggering bot-failure handoff",
                session_id,
            )
            if eff_track == "konsuler":
                await _trigger_bot_failure_handoff(chat_id, session_id, text, message, effective_locale)
                return

        for booking in bookings:
            if not should_send_qr(route.track, booking):
                continue
            await send_telegram_qr(
                chat_id,
                qr_payload=booking["qr_payload"],
                booking_code=booking["booking_code"],
                magic_url=booking["magic_url"],
                locale=effective_locale,
            )
        return
    unreachable: Never = route.action
    raise ValueError(f"unhandled route action: {unreachable}")


async def set_webhook(url: str) -> None:
    try:
        token = _telegram_token()
    except RuntimeError:
        logger.error("TELEGRAM_BOT_TOKEN is not configured; cannot set webhook")
        return
    payload: dict[str, str] = {"url": url}
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        payload["secret_token"] = secret
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json=payload,
        )
        data = response.json()
        if data.get("ok"):
            logger.info("Webhook set: %s", url)
        else:
            logger.error("Failed to set webhook: %s", data)


async def get_ngrok_url() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{NGROK_API}/api/tunnels")
            for tunnel in response.json().get("tunnels", []):
                public_url = tunnel.get("public_url", "")
                if isinstance(public_url, str) and public_url.startswith("https://"):
                    return public_url
    except Exception:
        return None
    return None


async def _handoff_timeout_loop() -> None:
    """Background task: check and resolve timed-out handoff sessions every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        try:
            resolved = await check_and_resolve_timed_out_handoffs(
                bot_token=_telegram_token(),
                staff_group_id=KJRI_STAFF_GROUP_ID,
            )
            if resolved:
                logger.info("Auto-resolved %d timed-out handoff(s)", resolved)
        except Exception:
            logger.exception("Error in handoff timeout loop")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    webhook_base = WEBHOOK_BASE_URL.strip()
    if not webhook_base:
        for _ in range(10):
            webhook_base = await get_ngrok_url() or ""
            if webhook_base:
                break
            logger.info("Waiting for ngrok...")
            await asyncio.sleep(3)

    if webhook_base:
        await set_webhook(f"{webhook_base.rstrip('/')}/webhook")
    else:
        logger.warning(
            "No webhook URL available. Set WEBHOOK_BASE_URL or ensure ngrok is running."
        )
    timeout_task = asyncio.create_task(_handoff_timeout_loop())
    try:
        yield
    finally:
        timeout_task.cancel()
        try:
            await timeout_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Temujanji KJRI Telegram webhook", lifespan=lifespan)


def _validate_secret(received_secret: str | None) -> None:
    configured_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if configured_secret and received_secret != configured_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram webhook secret",
        )


@app.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    _validate_secret(x_telegram_bot_api_secret_token)
    update: dict[str, Any] = await request.json()
    message = update.get("message")
    if not isinstance(message, dict):
        return {"ok": True}
    sender = message.get("from")
    chat = message.get("chat")
    text = message.get("text")
    if (
        not isinstance(sender, dict)
        or not isinstance(chat, dict)
        or not isinstance(sender.get("id"), int)
        or not isinstance(chat.get("id"), int)
        or not isinstance(text, str)
    ):
        return {"ok": True}

    try:
        await handle_inbound(chat["id"], text, sender["id"], sender=sender)
    except Exception as error:
        logger.exception("Failed to process Telegram update: %s", error)
        try:
            error_locale: Locale | None = None
            failed_session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=f"telegram-{sender['id']}",
                session_id=f"telegram-{chat['id']}",
            )
            if failed_session is not None:
                error_locale = parse_locale(failed_session.state.get("locale"))
            await send_telegram_message(
                chat["id"],
                t(error_locale, "error"),
            )
        except Exception:
            logger.exception("Failed to send error reply to Telegram")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to process Telegram message",
            ) from error
    return {"ok": True}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
