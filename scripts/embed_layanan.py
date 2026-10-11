"""Populate konsuler.layanan_konsuler.embedding using Gemini embeddings.

Run from the repo root:
    uv run python scripts/embed_layanan.py

Reads every row, builds a searchable text from nama_pelayanan + syarat JSON,
embeds it via gemini-embedding-001 (3072 dims), and writes it back.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from agent.embedding import embed_text  # noqa: E402

SELECT_SQL = """
SELECT id, nama_pelayanan, syarat
FROM konsuler.layanan_konsuler
ORDER BY id
"""

UPDATE_SQL = """
UPDATE konsuler.layanan_konsuler
SET embedding = %s::vector
WHERE id = %s
"""


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(map(str, vector)) + "]"


def _db_url() -> str:
    raw = os.environ.get(
        "DATABASE_URL",
        "postgresql://temujanji:temujanji@localhost:5432/temujanji",
    )
    if raw.startswith("postgresql+asyncpg://"):
        raw = "postgresql://" + raw.removeprefix("postgresql+asyncpg://")
    return raw


def _embed_text(nama: str, syarat: dict) -> str:
    return f"{nama}\n{json.dumps(syarat, ensure_ascii=False)}"


def main() -> int:
    with psycopg.connect(
        _db_url(), row_factory=dict_row, options="-c search_path=konsuler,public"
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(SELECT_SQL)
            rows = cur.fetchall()

        print(f"Found {len(rows)} rows to embed.")
        for idx, row in enumerate(rows, start=1):
            nama = row["nama_pelayanan"] or ""
            syarat = row["syarat"] or {}
            vector = list(embed_text(_embed_text(nama, syarat)))
            literal = _vector_literal(vector)
            with conn.cursor() as cur:
                cur.execute(UPDATE_SQL, (literal, row["id"]))
            conn.commit()
            print(f"[{idx}/{len(rows)}] embedded {row['id']}: {nama}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
