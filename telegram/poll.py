"""Local Telegram long-polling runner (no public webhook required).

Called by: `uv run python -m telegram.poll` / host process for local testing.
Does not define DB schemas. User instruction: jalankan lagi dengan telegram + bot token.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

from telegram.bot import handle_inbound, send_telegram_message  # noqa: E402


async def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not configured")

    api = f"https://api.telegram.org/bot{token}"
    offset = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        await client.get(f"{api}/deleteWebhook", params={"drop_pending_updates": True})
        me = (await client.get(f"{api}/getMe")).json()["result"]
        print(f"Polling as @{me['username']} (Ctrl+C to stop)")

        while True:
            try:
                response = await client.get(
                    f"{api}/getUpdates",
                    params={"timeout": 30, "offset": offset},
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                print(f"getUpdates error (retrying in 5s): {error}")
                await asyncio.sleep(5)
                continue
            updates = response.json().get("result", [])
            for update in updates:
                offset = max(offset, int(update["update_id"]) + 1)
                message = update.get("message") or {}
                sender = message.get("from") or {}
                chat = message.get("chat") or {}
                text = message.get("text")
                if not (
                    isinstance(sender.get("id"), int)
                    and isinstance(chat.get("id"), int)
                    and isinstance(text, str)
                ):
                    continue
                try:
                    await handle_inbound(chat["id"], text, sender["id"])
                except Exception as error:  # noqa: BLE001 - keep poller alive
                    print(f"error handling update: {error}")
                    try:
                        await send_telegram_message(
                            chat["id"],
                            "Maaf, pesan Anda belum bisa diproses. Silakan coba lagi sebentar.",
                        )
                    except httpx.HTTPError as send_error:
                        print(f"failed to send error reply: {send_error}")


if __name__ == "__main__":
    asyncio.run(main())
