import json

import pytest

from agent.konsuler import tools


@pytest.fixture(autouse=True)
def reset_konsuler_hooks():
    captured: list[tuple[str, tuple]] = []

    def execute(sql: str, params: tuple) -> list[dict]:
        captured.append((sql, params))
        return []

    tools.set_execute(execute)
    tools.set_embedder(lambda text: [0.25, 0.75])
    yield captured
    tools.set_execute(None)
    tools.set_embedder(None)


def test_cari_layanan_queries_qualified_konsuler_table(reset_konsuler_hooks):
    reset_konsuler_hooks.clear()

    def execute(sql: str, params: tuple) -> list[dict]:
        reset_konsuler_hooks.append((sql, params))
        return [
            {
                "kode_pelayanan": "PSP-001",
                "nama_pelayanan": "Paspor - Pekerja Formal",
                "biaya_aed": 390,
            }
        ]

    tools.set_execute(execute)

    result = tools.cari_layanan("paspor")

    sql, params = reset_konsuler_hooks[0]
    assert "konsuler.layanan_konsuler" in sql
    assert "FROM layanan_konsuler" not in sql.replace("konsuler.layanan_konsuler", "")
    assert "temujanji." not in sql
    assert params == ("paspor",)
    assert result[0]["kode_pelayanan"] == "PSP-001"


def test_get_detail_layanan_queries_qualified_konsuler_table(reset_konsuler_hooks):
    reset_konsuler_hooks.clear()

    def execute(sql: str, params: tuple) -> list[dict]:
        reset_konsuler_hooks.append((sql, params))
        return [{"kode_pelayanan": "PSP-001", "syarat": {"wajib": ["paspor"]}}]

    tools.set_execute(execute)

    result = tools.get_detail_layanan("PSP-001")

    sql, params = reset_konsuler_hooks[0]
    assert "konsuler.layanan_konsuler" in sql
    assert params[0] == "PSP-001"
    assert set(params) == {"PSP-001"}
    assert result[0]["kode_pelayanan"] == "PSP-001"


def test_cari_layanan_semantik_uses_injected_embedding_and_pgvector(
    reset_konsuler_hooks,
):
    reset_konsuler_hooks.clear()

    def execute(sql: str, params: tuple) -> list[dict]:
        reset_konsuler_hooks.append((sql, params))
        return [{"kode_pelayanan": "LHR-001", "similarity_score": 0.91}]

    tools.set_execute(execute)
    tools.set_embedder(lambda text: [0.1, 0.2, 0.3])

    result = tools.cari_layanan_semantik("anak saya baru lahir di Dubai")

    sql, params = reset_konsuler_hooks[0]
    assert "konsuler.layanan_konsuler" in sql
    assert "<=>" in sql
    assert params[0] == [0.1, 0.2, 0.3]
    assert all(param == [0.1, 0.2, 0.3] for param in params)
    assert result[0]["kode_pelayanan"] == "LHR-001"


def test_simpan_identitas_inserts_into_konsuler_pengguna(reset_konsuler_hooks):
    reset_konsuler_hooks.clear()

    def execute(sql: str, params: tuple) -> list[dict]:
        reset_konsuler_hooks.append((sql, params))
        return [{"id": "11111111-1111-1111-1111-111111111111", "nama_lengkap": "Siti"}]

    tools.set_execute(execute)

    result = tools.simpan_identitas(
        "session-1",
        "Siti",
        json.dumps({"nomor_paspor": "A1234567", "kota_domisili": "Dubai"}),
    )

    sql, params = reset_konsuler_hooks[0]
    assert "INSERT INTO konsuler.pengguna" in sql
    assert params[0] == "session-1"
    assert params[1] == "Siti"
    assert params[2] == "A1234567"
    assert result["nama_lengkap"] == "Siti"


def test_simpan_interaksi_inserts_into_konsuler_chat_sessions(reset_konsuler_hooks):
    reset_konsuler_hooks.clear()

    def execute(sql: str, params: tuple) -> list[dict]:
        reset_konsuler_hooks.append((sql, params))
        return [{"id": "22222222-2222-2222-2222-222222222222"}]

    tools.set_execute(execute)

    result = tools.simpan_interaksi(
        "session-1",
        "Siti",
        "PSP-001",
        "syarat paspor?",
        "bawa paspor lama",
        "2",
        '["cari-layanan"]',
        "telegram",
        "11111111-1111-1111-1111-111111111111",
    )

    sql, params = reset_konsuler_hooks[0]
    assert "INSERT INTO konsuler.chat_sessions" in sql
    assert params[0] == "session-1"
    assert params[7] == "telegram"
    assert result["id"] == "22222222-2222-2222-2222-222222222222"
