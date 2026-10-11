"""SQL tools that only touch the konsuler schema."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from typing import Any

ExecuteFn = Callable[[str, tuple[Any, ...]], list[dict[str, Any]]]
EmbedFn = Callable[[str], Sequence[float]]

_execute: ExecuteFn | None = None
_embedder: EmbedFn | None = None
_channel: ContextVar[str | None] = ContextVar("konsuler_channel", default=None)

CARI_LAYANAN_SQL = """
SELECT kode_pelayanan, nama_pelayanan, biaya_aed, biaya_keterangan
FROM konsuler.layanan_konsuler
WHERE LOWER(nama_pelayanan) LIKE '%%' || LOWER(%s) || '%%'
ORDER BY nama_pelayanan
LIMIT 10
"""

GET_DETAIL_SQL = """
SELECT kode_pelayanan, nama_pelayanan, syarat, biaya_aed, biaya_keterangan
FROM konsuler.layanan_konsuler
WHERE LOWER(nama_pelayanan) LIKE '%%' || LOWER(%s) || '%%'
   OR UPPER(kode_pelayanan) = UPPER(%s)
LIMIT 5
"""

CARI_SEMANTIK_SQL = """
SELECT kode_pelayanan, nama_pelayanan, biaya_aed, biaya_keterangan,
       1 - (embedding <=> %s::vector) AS similarity_score
FROM konsuler.layanan_konsuler
WHERE embedding IS NOT NULL
ORDER BY embedding <=> %s::vector
LIMIT 5
"""

SIMPAN_IDENTITAS_SQL = """
INSERT INTO konsuler.pengguna (
    session_id, nama_lengkap, nomor_paspor, nomor_ic, nomor_telepon,
    email, alamat_domisili, kota_domisili, jenis_identitas_lain, nomor_identitas_lain
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id, nama_lengkap, created_at
"""

SIMPAN_INTERAKSI_SQL = """
INSERT INTO konsuler.chat_sessions (
    session_id, nama_pengguna, layanan_diminta, pesan_user, pesan_agent,
    jumlah_pesan, tools_dipanggil, channel, pengguna_id
) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::uuid)
RETURNING id, created_at
"""

GET_STATISTIK_SQL = """
SELECT layanan_diminta,
       COUNT(*) AS jumlah_interaksi,
       MIN(created_at) AS pertama_ditanya,
       MAX(created_at) AS terakhir_ditanya
FROM konsuler.chat_sessions
WHERE layanan_diminta IS NOT NULL
  AND created_at >= COALESCE(%s::timestamptz, '1970-01-01'::timestamptz)
  AND created_at <= COALESCE(%s::timestamptz, NOW())
GROUP BY layanan_diminta
ORDER BY jumlah_interaksi DESC
LIMIT 20
"""


def set_execute(fn: ExecuteFn | None) -> None:
    global _execute
    _execute = fn


def set_embedder(fn: EmbedFn | None) -> None:
    global _embedder
    _embedder = fn


def set_channel(channel: str | None) -> None:
    """Bind the source channel (e.g. 'telegram') for the current invocation."""
    _channel.set(channel)


def _run(sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    if _execute is not None:
        return _execute(sql, params)
    return _default_execute(sql, params)


def _default_execute(sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    raw = os.environ.get(
        "DATABASE_URL",
        "postgresql://temujanji:temujanji@localhost:5432/temujanji",
    )
    if raw.startswith("postgresql+asyncpg://"):
        raw = "postgresql://" + raw.removeprefix("postgresql+asyncpg://")
    with psycopg.connect(
        raw,
        row_factory=dict_row,
        options="-c search_path=konsuler,public",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = list(cur.fetchall()) if cur.description is not None else []
        conn.commit()
    return rows


def _embed(text: str) -> Sequence[float]:
    if _embedder is not None:
        return _embedder(text)
    raise RuntimeError("konsuler embedder is not configured")


def _embed_or_none(text: str) -> Sequence[float] | None:
    if _embedder is not None:
        return _embedder(text)
    return None


def _vector_literal(vector: Sequence[float]) -> str:
    """Render a float sequence as a pgvector literal string, e.g. [0.1,0.2]."""
    return "[" + ",".join(map(str, vector)) + "]"


def cari_layanan(keyword: str) -> list[dict[str, Any]]:
    """Cari layanan konsuler KJRI Dubai berdasarkan kata kunci nama."""
    return _run(CARI_LAYANAN_SQL, (keyword,))


def get_detail_layanan(kode_atau_nama: str) -> list[dict[str, Any]]:
    """Ambil syarat dan biaya layanan dari schema konsuler."""
    return _run(GET_DETAIL_SQL, (kode_atau_nama, kode_atau_nama))


def cari_layanan_semantik(query: str) -> list[dict[str, Any]]:
    """Cari layanan konsuler dengan embedding + jarak pgvector."""
    vector = _embed_or_none(query)
    if vector is None:
        return []
    literal = _vector_literal(vector)
    return _run(CARI_SEMANTIK_SQL, (literal, literal))


def _coerce_json_array(value: str) -> str:
    """Return value as a JSONB-safe array string, or '[]' when unparseable."""
    if not value:
        return "[]"
    try:
        parsed = json.loads(value)
        return json.dumps(parsed)
    except (ValueError, TypeError):
        return json.dumps([value])


def _coerce_uuid(value: str | None) -> str | None:
    """Return value only when it is a valid UUID, else None."""
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError):
        return None


def simpan_identitas(
    session_id: str, nama_lengkap: str, data_tambahan: str = "{}"
) -> dict[str, Any]:
    """Simpan identitas WNI ke konsuler.pengguna."""
    try:
        extra = json.loads(data_tambahan or "{}")
    except (ValueError, TypeError):
        extra = {}
    rows = _run(
        SIMPAN_IDENTITAS_SQL,
        (
            session_id,
            nama_lengkap,
            extra.get("nomor_paspor"),
            extra.get("nomor_ic"),
            extra.get("nomor_telepon"),
            extra.get("email"),
            extra.get("alamat_domisili"),
            extra.get("kota_domisili"),
            extra.get("jenis_identitas_lain"),
            extra.get("nomor_identitas_lain"),
        ),
    )
    return rows[0] if rows else {}


def simpan_interaksi(
    session_id: str,
    nama_pengguna: str,
    layanan_diminta: str,
    pesan_user: str,
    pesan_agent: str,
    jumlah_pesan: str,
    tools_dipanggil: str,
    channel: str,
    pengguna_id: str,
) -> dict[str, Any]:
    """Catat interaksi chatbot ke konsuler.chat_sessions."""
    try:
        jumlah = int(jumlah_pesan)
    except (ValueError, TypeError):
        jumlah = 1
    resolved_channel = _channel.get() or channel or "web"
    rows = _run(
        SIMPAN_INTERAKSI_SQL,
        (
            session_id,
            nama_pengguna,
            layanan_diminta,
            pesan_user,
            pesan_agent,
            jumlah,
            _coerce_json_array(tools_dipanggil),
            resolved_channel,
            _coerce_uuid(pengguna_id),
        ),
    )
    return rows[0] if rows else {}


def _coerce_optional_date(value: str | None) -> str | None:
    """Return a non-empty ISO date string, or None for SQL NULL."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def get_statistik_penggunaan(
    dari_tanggal: str = "", sampai_tanggal: str = ""
) -> list[dict[str, Any]]:
    """Statistik layanan yang paling sering ditanyakan (admin)."""
    return _run(
        GET_STATISTIK_SQL,
        (
            _coerce_optional_date(dari_tanggal),
            _coerce_optional_date(sampai_tanggal),
        ),
    )
