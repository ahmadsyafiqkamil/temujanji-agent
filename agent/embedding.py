"""Gemini embedding helper for konsuler semantic search.

The konsuler.layanan_konsuler.embedding column is vector(3072), which matches
Google's gemini-embedding-001 output dimension.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import httpx

EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
EMBED_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{EMBED_MODEL}:embedContent"
)


def _api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    )


def embed_text(text: str) -> Sequence[float]:
    """Return a 3072-dim embedding vector for ``text`` using Gemini."""
    key = _api_key()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY or GOOGLE_API_KEY is not configured for embeddings"
        )
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{EMBED_URL}?key={key}",
            json={"content": {"parts": [{"text": text}]}},
        )
        response.raise_for_status()
        data = response.json()
    return data["embedding"]["values"]
