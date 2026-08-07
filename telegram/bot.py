"""Telegram webhook adapter for the KJRI appointment agent."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, status
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agent import root_agent
from agent.tools import set_telegram_user_id

APP_NAME = "temujanji_telegram"
session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)
app = FastAPI(title="Temujanji KJRI Telegram webhook")


async def send_telegram_message(chat_id: int, text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        response.raise_for_status()


async def run_agent(user_id: int, chat_id: int, text: str) -> tuple[list[str], list[str]]:
    """Run one message through ADK and return text replies and newly created magic URLs."""
    session_id = f"telegram-{chat_id}"
    adk_user_id = f"telegram-{user_id}"
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=adk_user_id,
        session_id=session_id,
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=adk_user_id,
            session_id=session_id,
        )

    set_telegram_user_id(str(user_id))
    replies: list[str] = []
    magic_urls: list[str] = []
    message = types.Content(role="user", parts=[types.Part.from_text(text=text)])
    async for event in runner.run_async(
        user_id=adk_user_id,
        session_id=session_id,
        new_message=message,
    ):
        for function_response in event.get_function_responses():
            response = function_response.response or {}
            magic_url = response.get("magic_url")
            if isinstance(magic_url, str):
                magic_urls.append(magic_url)
        if event.is_final_response() and event.content:
            for part in event.content.parts or []:
                if part.text:
                    replies.append(part.text)
    return replies, magic_urls


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
        replies, magic_urls = await run_agent(sender["id"], chat["id"], text)
        for reply in replies:
            await send_telegram_message(chat["id"], reply)
        for magic_url in magic_urls:
            await send_telegram_message(chat["id"], f"Tautan janji temu Anda: {magic_url}")
    except (httpx.HTTPError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to process Telegram message",
        ) from error
    return {"ok": True}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
