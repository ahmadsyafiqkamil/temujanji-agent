"""Telegram webhook adapter for the KJRI appointment agent."""

from __future__ import annotations

import asyncio
import io
import logging
import os
from contextlib import asynccontextmanager
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


async def handle_inbound(chat_id: int, text: str, user_id: int) -> None:
    session_id = f"telegram-{chat_id}"
    adk_user_id = f"telegram-{user_id}"
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
        replies, bookings = await run_agent(
            user_id,
            chat_id,
            text,
            track=route.track,
            locale=effective_locale,
        )
        hidden = remove_keyboard()
        for reply in replies:
            await send_telegram_message(chat_id, reply, reply_markup=hidden)
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
    yield


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
        await handle_inbound(chat["id"], text, sender["id"])
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
