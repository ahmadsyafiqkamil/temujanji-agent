CREATE TABLE IF NOT EXISTS konsuler.layanan_konsuler (
    id               SERIAL          PRIMARY KEY,
    kode_pelayanan   VARCHAR(20)     NOT NULL UNIQUE,
    nama_pelayanan   TEXT            NOT NULL,
    syarat           JSONB           NOT NULL,
    biaya_aed        NUMERIC(10, 2),
    biaya_keterangan TEXT,
    embedding        vector(3072)
);

CREATE INDEX IF NOT EXISTS idx_layanan_syarat
    ON konsuler.layanan_konsuler USING GIN (syarat);

CREATE TABLE IF NOT EXISTS konsuler.pengguna (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              VARCHAR(255)    NOT NULL,
    nama_lengkap            VARCHAR(255)    NOT NULL,
    nomor_paspor            VARCHAR(20),
    nomor_ic                VARCHAR(30),
    nomor_telepon           VARCHAR(20),
    email                   VARCHAR(255),
    alamat_domisili         TEXT,
    kota_domisili           VARCHAR(100),
    jenis_identitas_lain    VARCHAR(50),
    nomor_identitas_lain    VARCHAR(50),
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pengguna_session_id
    ON konsuler.pengguna (session_id);

CREATE TABLE IF NOT EXISTS konsuler.chat_sessions (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      VARCHAR(255)    NOT NULL,
    nama_pengguna   VARCHAR(255),
    layanan_diminta VARCHAR(255),
    pesan_user      TEXT,
    pesan_agent     TEXT,
    jumlah_pesan    INTEGER         DEFAULT 1,
    tools_dipanggil JSONB           DEFAULT '[]'::jsonb,
    channel         VARCHAR(50)     DEFAULT 'web',
    ip_address      INET,
    user_agent      TEXT,
    pengguna_id     UUID            REFERENCES konsuler.pengguna(id),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id
    ON konsuler.chat_sessions (session_id);
