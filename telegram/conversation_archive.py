"""Conversation closure detection and transcript archiving for Temujanji agent.

Migrated from Chatbot KJRI Dubai ``conversation_archive.py``; adapted from
psycopg2 to psycopg (v3) and from schema ``public`` to ``konsuler``.
"""

from __future__ import annotations

import json
import logging
import os
import re

import psycopg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Closure detection
# ---------------------------------------------------------------------------

_GRATITUDE_PATTERNS = re.compile(
    r"terima\s*kasih|makasih|thank\s*you|thanks|"
    r"sampai\s*jumpa|selamat\s*tinggal|bye|goodbye|dadah|"
    r"sudah\s*(?:cukup|selesai)",
    re.IGNORECASE,
)

# If any of these signals are present alongside a gratitude keyword,
# treat the message as a continuation rather than a closure.
_CONTINUATION_SIGNALS = re.compile(
    r"\?|tapi|tetapi|namun|satu\s*lagi|mau\s*tanya|ada\s*lagi|"
    r"bagaimana|gimana|berapa|apakah|bisa\s*tolong",
    re.IGNORECASE,
)


def detect_gratitude_closure(text: str) -> str | None:
    """Return 'gratitude' if text is a clean farewell/thank-you, else None.

    Anti-false-positive heuristic: if continuation signals (question mark,
    'tapi', 'mau tanya', interrogative words) are present alongside a
    gratitude keyword, return None (user is continuing the conversation).
    """
    if not _GRATITUDE_PATTERNS.search(text):
        return None
    if _CONTINUATION_SIGNALS.search(text):
        return None
    return "gratitude"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn_string() -> str:
    raw = os.environ.get(
        "DATABASE_URL",
        "postgresql://temujanji:temujanji@localhost:5432/temujanji",
    )
    if raw.startswith("postgresql+asyncpg://"):
        raw = "postgresql://" + raw.removeprefix("postgresql+asyncpg://")
    return raw


def save_conversation_archive(
    session_id: str,
    channel: str,
    on: str,
    transcript_messages: list[dict],
    pengguna_id: str | None = None,
) -> str | None:
    """Insert a conversation archive row. Returns archive UUID or None on error.

    transcript_messages: list of {"role": str, "text": str, "at": str (ISO 8601)}
    on: closure reason code (e.g. "gratitude")
    Error handling: logs exception and returns None — never raises, so UX is not broken.
    """
    transcript = json.dumps(
        {
            "schema_version": "1",
            "closure_reason": on,
            "messages": transcript_messages,
        },
        ensure_ascii=False,
    )
    try:
        with psycopg.connect(_get_conn_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO konsuler.conversation_archives
                        (session_id, channel, "on", transcript, pengguna_id)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    RETURNING id
                    """,
                    (session_id, channel, on, transcript, pengguna_id),
                )
                row = cur.fetchone()
                archive_id = str(row[0]) if row else None
            conn.commit()
        logger.info(
            "Conversation archive saved: id=%s session=%s on=%s messages=%d",
            archive_id,
            session_id,
            on,
            len(transcript_messages),
        )
        return archive_id
    except Exception:
        logger.exception(
            "Failed to save conversation archive for session=%s", session_id
        )
        return None
