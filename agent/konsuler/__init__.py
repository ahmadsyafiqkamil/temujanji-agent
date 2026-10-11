"""Consular-knowledge tools scoped to the konsuler Postgres schema."""

from agent.embedding import embed_text
from agent.konsuler import tools

# Wire the Gemini embedder so cari_layanan_semantik works at runtime.
# Tests override this via tools.set_embedder(...) in their own fixtures.
tools.set_embedder(embed_text)
