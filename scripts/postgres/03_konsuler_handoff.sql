-- Human Agent Handoff + Conversation Archive (schema konsuler)
-- Migrasi dari Chatbot KJRI Dubai (migrations/006_007_008) ke Temujanji.
-- Tables: konsuler.handoff_queue, konsuler.conversation_archives

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS konsuler.handoff_queue (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          TEXT        NOT NULL,
    pengguna_id         UUID        REFERENCES konsuler.pengguna(id),
    user_chat_id        BIGINT      NOT NULL,
    nama_user           TEXT,
    pertanyaan_terakhir TEXT,
    layanan_dicari      TEXT,
    status              TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'in_progress', 'resolved')),
    last_activity_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_handoff_session_id    ON konsuler.handoff_queue(session_id);
CREATE INDEX IF NOT EXISTS idx_handoff_status        ON konsuler.handoff_queue(status);
CREATE INDEX IF NOT EXISTS idx_handoff_last_activity ON konsuler.handoff_queue(last_activity_at)
    WHERE status IN ('pending', 'in_progress');

CREATE TABLE IF NOT EXISTS konsuler.conversation_archives (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  TEXT        NOT NULL,
    channel     TEXT        NOT NULL,
    "on"        TEXT        NOT NULL,
    transcript  JSONB       NOT NULL,
    pengguna_id UUID        REFERENCES konsuler.pengguna(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_archives_session_id ON konsuler.conversation_archives(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_archives_created_at ON konsuler.conversation_archives(created_at);
