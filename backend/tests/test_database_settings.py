from temujanji.settings import _database_from_env


def test_postgres_database_uses_temujanji_search_path(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://temujanji:temujanji@localhost:5432/temujanji",
    )

    config = _database_from_env()

    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["OPTIONS"]["options"] == "-c search_path=temujanji,public"


def test_sqlite_database_omits_search_path(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    config = _database_from_env()

    assert config["ENGINE"] == "django.db.backends.sqlite3"
    assert "OPTIONS" not in config
