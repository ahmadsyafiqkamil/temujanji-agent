-- =============================================================================
-- RAG Database - Layanan Konsuler KJRI Dubai
-- PostgreSQL
-- Sumber: Persyaratan Pelayanan Kekonsuleran (dokumen internal KJRI Dubai)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DDL: Buat tabel
-- -----------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS layanan_konsuler (
    id               SERIAL          PRIMARY KEY,
    kode_pelayanan   VARCHAR(20)     NOT NULL UNIQUE,
    nama_pelayanan   TEXT            NOT NULL,
    syarat           JSONB           NOT NULL,
    biaya_aed        NUMERIC(10, 2),
    biaya_keterangan TEXT,
    embedding        vector(3072)
);

-- GIN index pada kolom JSONB untuk query syarat yang cepat
CREATE INDEX IF NOT EXISTS idx_layanan_syarat
    ON layanan_konsuler USING GIN (syarat);

-- Catatan: index vector tidak dibuat di sini karena harus dibuat setelah
-- data ter-embed (ivfflat perlu data untuk menentukan centroid).
-- Jalankan scripts/seed_embeddings.py terlebih dahulu, lalu buat index:
-- CREATE INDEX idx_layanan_embedding ON layanan_konsuler
--   USING hnsw (embedding vector_cosine_ops);

-- -----------------------------------------------------------------------------
-- DML: Insert data
-- Kolom syarat dibagi 3 kategori:
--   "wajib"      : dokumen/syarat yang mutlak harus dipenuhi
--   "kondisional": syarat yang hanya berlaku pada kondisi tertentu
--   "catatan"    : instruksi teknis / ketentuan tambahan
-- -----------------------------------------------------------------------------

INSERT INTO layanan_konsuler (kode_pelayanan, nama_pelayanan, syarat, biaya_aed, biaya_keterangan)
VALUES

-- --------------------------------------------------------------------------
-- PSP-001: Paspor - Pekerja Formal
-- --------------------------------------------------------------------------
(
    'PSP-001',
    'Paspor - Pekerja Formal',
    '{
        "wajib": [
            "Membuat janji temu pada halaman: www.kjridubai.id",
            "Paspor asli beserta salinannya",
            "Salinan residence visa, kartu Emirates ID yang masih berlaku",
            "Salinan Kartu Tanda Penduduk (KTP) / Kartu Keluarga (KK) / Akta Kelahiran / Ijazah",
            "NOC / surat keterangan bekerja / kontrak kerja dari perusahaan"
        ],
        "kondisional": [
            "Apabila pindah kerja: fotokopi cancellation visa dan offer letter yang ditandatangani ke dua belah pihak"
        ],
        "catatan": [
            "Pemohon harus datang untuk biometrik",
            "Berpakaian rapi / kemeja dan berkerah (selain warna putih)"
        ]
    }',
    100.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- PSP-002: Paspor - Pekerja Domestik
-- --------------------------------------------------------------------------
(
    'PSP-002',
    'Paspor - Pekerja Domestik',
    '{
        "wajib": [
            "Membuat janji temu pada halaman: www.kjridubai.id",
            "Paspor asli beserta salinannya",
            "Salinan residence visa, kartu Emirates ID yang masih berlaku",
            "Salinan Kartu Tanda Penduduk (KTP) / Kartu Keluarga (KK) / Akta Kelahiran / Ijazah",
            "Salinan kartu Emirates ID / Paspor Majikan",
            "Surat keterangan bekerja / kontrak kerja dari Kementerian Tenaga Kerja UAE (Mohre)"
        ],
        "kondisional": [
            "Apabila pindah kerja: fotokopi cancellation visa dan offer letter yang ditandatangani ke dua belah pihak"
        ],
        "catatan": [
            "Pemohon harus datang untuk biometrik",
            "Berpakaian rapi / kemeja dan berkerah (selain warna putih)"
        ]
    }',
    100.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- PSP-003: Paspor Baru - Anak Baru Lahir
-- --------------------------------------------------------------------------
(
    'PSP-003',
    'Paspor Baru - Anak Baru Lahir',
    '{
        "wajib": [
            "Membuat janji temu pada halaman: www.kjridubai.id",
            "Akta lahir yang diterbitkan dan dilegalisasi oleh MOFAIC UAE beserta salinannya",
            "Salinan paspor, residence visa, kartu Emirates ID (orang tua) yang masih berlaku",
            "Salinan akta nikah orang tua yang sudah dilegalisir oleh MOFAIC UAE",
            "Salinan Kartu Tanda Penduduk (KTP) / Kartu Keluarga (KK) orang tua"
        ],
        "kondisional": [
            "Untuk anak pemegang kewarganegaraan ganda: NOC dari orang tua non-WNI yang menyatakan tidak ada keberatan bagi anak untuk memiliki kewarganegaraan Indonesia",
            "Pernyataan dari orang tua WNI di atas materai Rp10.000,- yang ditandatangani di hadapan petugas KJRI",
            "Salinan Emirates ID anak (apabila ada)",
            "Salinan paspor asing anak (apabila ada)"
        ],
        "catatan": [
            "Pemohon harus datang untuk biometrik"
        ]
    }',
    100.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- PSP-004: Legalisasi Akta Lahir - Anak Baru Lahir
-- --------------------------------------------------------------------------
(
    'PSP-004',
    'Legalisasi Akta Lahir - Anak Baru Lahir',
    '{
        "wajib": [
            "Akta lahir yang diterbitkan dan dilegalisasi oleh MOFAIC UAE beserta salinannya",
            "Salinan akta nikah orang tua yang telah dilegalisir oleh MOFAIC UAE",
            "Salinan paspor, residence visa, kartu Emirates ID (orang tua) yang masih berlaku"
        ],
        "kondisional": [
            "Salinan paspor asing anak (apabila ada)"
        ],
        "catatan": []
    }',
    95.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- PSP-005: Paspor Rusak
-- --------------------------------------------------------------------------
(
    'PSP-005',
    'Paspor Rusak',
    '{
        "wajib": [
            "Membuat janji temu pada halaman: www.kjridubai.id",
            "Paspor lama beserta salinannya",
            "Salinan Emirates ID / Visa izin tinggal yang masih berlaku",
            "Salinan Kartu Tanda Penduduk (KTP) / Kartu Keluarga (KK)",
            "Surat keterangan bekerja / kontrak kerja dari Perusahaan / Kementerian Tenaga Kerja UAE (Mohre)"
        ],
        "kondisional": [
            "Salinan kartu Emirates ID / Paspor Majikan (khusus pekerja domestik)"
        ],
        "catatan": [
            "Pemohon harus datang untuk biometrik",
            "Berpakaian rapi / kemeja dan berkerah (selain warna putih)"
        ]
    }',
    230.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- PSP-006: Paspor Hilang
-- --------------------------------------------------------------------------
(
    'PSP-006',
    'Paspor Hilang',
    '{
        "wajib": [
            "Membuat janji temu pada halaman: www.kjridubai.id",
            "Salinan residence visa, kartu Emirates ID yang masih berlaku",
            "Salinan paspor dan kartu Emirates ID (majikan / sponsor)",
            "Salinan Kartu Tanda Penduduk (KTP) / Kartu Keluarga (KK)",
            "Sertifikat kehilangan paspor dari kantor polisi setempat dengan masa berlaku 1 (satu) bulan dari tanggal terbit",
            "Kontrak kerja dari Imigrasi / MOHRE (berbahasa Inggris)"
        ],
        "kondisional": [
            "Salinan paspor lama (jika ada) atau data diri keimigrasian / tafasil iqomah"
        ],
        "catatan": [
            "Pemohon harus datang untuk biometrik",
            "Berpakaian rapi / kemeja dan berkerah (selain warna putih)"
        ]
    }',
    360.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- SPLP-001: SPLP - PMI Resmi (Ada Sponsor)
-- --------------------------------------------------------------------------
(
    'SPLP-001',
    'SPLP (Surat Perjalanan Laksana Paspor) - PMI Resmi / Ada Sponsor',
    '{
        "wajib": [
            "Membuat janji temu / appointment di www.kjridubai.id",
            "Registrasi layanan konsuler di www.kjridubai.org",
            "Paspor asli dan fotokopi paspor",
            "Fotokopi Emirates ID (depan dan belakang)",
            "Fotokopi Emirates ID / Paspor Sponsor",
            "Cancel Visa",
            "Foto 2 lembar (background putih)"
        ],
        "kondisional": [],
        "catatan": []
    }',
    25.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- SPLP-002: SPLP - PMI Tidak Resmi (Kaburan)
-- --------------------------------------------------------------------------
(
    'SPLP-002',
    'SPLP (Surat Perjalanan Laksana Paspor) - PMI Tidak Resmi / Kaburan',
    '{
        "wajib": [
            "Surat keterangan hilang paspor dari kepolisian UAE",
            "Fotokopi paspor sebelumnya",
            "Foto 2 lembar (background putih)"
        ],
        "kondisional": [
            "Fotokopi Emirates ID (opsional)"
        ],
        "catatan": []
    }',
    25.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- SPLP-003: Surat Keterangan Kirim Barang Kargo
-- --------------------------------------------------------------------------
(
    'SPLP-003',
    'Surat Keterangan Kirim Barang Kargo',
    '{
        "wajib": [
            "Surat dari perusahaan kargo",
            "Fotokopi Paspor, Emirates ID / Visa",
            "Packing List"
        ],
        "kondisional": [],
        "catatan": []
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
);

-- -----------------------------------------------------------------------------
-- Verifikasi
-- -----------------------------------------------------------------------------

-- =============================================================================
-- INSERT LANJUTAN
-- Sumber dokumen tambahan:
--   3. Persyaratan Legalisasi.docx
--   4. SYARAT LAPOR DIRI.docx
--   5. SYARAT VISA ENGLISH ARABIC 2024.docx
--   PERSYARATAN LAYANAN AFFIDAFIT.docx
--   PERSYARATAN PENDUL2024.docx
--   SYARAT NIKAH Di KJRI Dubai 2024.docx
-- =============================================================================

INSERT INTO layanan_konsuler (kode_pelayanan, nama_pelayanan, syarat, biaya_aed, biaya_keterangan)
VALUES

-- --------------------------------------------------------------------------
-- LEG-001: Legalisasi Dokumen Pribadi
-- --------------------------------------------------------------------------
(
    'LEG-001',
    'Legalisasi Dokumen Pribadi',
    '{
        "wajib": [
            "Seluruh dokumen yang ingin dilegalisasi harus sudah terlebih dahulu dilegalisasi oleh Kementerian Luar Negeri UAE (MOFAIC UAE)",
            "Salinan paspor pemilik dokumen",
            "Salinan Emirates ID pemilik dokumen"
        ],
        "kondisional": [],
        "catatan": [
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap",
            "Pengajuan langsung di Loket Konsuler KJRI Dubai: Senin-Jumat pukul 09.00-12.00",
            "Pengambilan dokumen: Senin-Kamis pukul 15.00-16.00"
        ]
    }',
    95.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- LEG-002: Legalisasi Dokumen Bisnis
-- --------------------------------------------------------------------------
(
    'LEG-002',
    'Legalisasi Dokumen Bisnis',
    '{
        "wajib": [
            "Seluruh dokumen yang ingin dilegalisasi harus sudah terlebih dahulu dilegalisasi oleh Kementerian Luar Negeri UAE (MOFAIC UAE)",
            "Salinan paspor pemilik dokumen",
            "Salinan Emirates ID pemilik dokumen",
            "Salinan izin bisnis (trade license)"
        ],
        "kondisional": [],
        "catatan": [
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap",
            "Pengajuan langsung di Loket Konsuler KJRI Dubai: Senin-Jumat pukul 09.00-12.00",
            "Pengambilan dokumen: Senin-Kamis pukul 15.00-16.00"
        ]
    }',
    460.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- SK-001: Surat Keterangan Nikah
-- --------------------------------------------------------------------------
(
    'SK-001',
    'Surat Keterangan Nikah',
    '{
        "wajib": [
            "Akta Nikah asli yang dikeluarkan oleh Dubai Court atau Pengadilan di Wilayah Emirat Utara, dilegalisasi oleh MOFAIC UAE (untuk pengajuan dan akan dikembalikan)",
            "Salinan Akta Nikah asli yang dilegalisasi oleh MOFAIC UAE",
            "Salinan paspor masing-masing suami dan istri, serta Visa Izin Tinggal (Residence Visa) yang masih berlaku",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [],
        "catatan": [
            "Diperlukan bagi WNI yang telah menikah di Dubai/Emirat Utara dan hendak mendaftarkan pernikahan di Indonesia",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap",
            "Harus ditandatangani pemohon langsung di depan petugas Konsuler KJRI Dubai"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- SK-002: Surat Keterangan Status Sipil
-- --------------------------------------------------------------------------
(
    'SK-002',
    'Surat Keterangan Status Sipil',
    '{
        "wajib": [
            "Surat Keterangan Status Perkawinan dari KUA atau Catatan Sipil Indonesia, tidak lebih dari 6 bulan, dilegalisasi oleh Kemenkumham RI dan Kemenlu RI",
            "Salinan paspor masing-masing suami dan istri, serta Visa Izin Tinggal (Residence Visa) yang masih berlaku",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [
            "Akta Perceraian (bagi yang telah bercerai)",
            "Akta Kematian pasangan (apabila pasangan sebelumnya telah meninggal)"
        ],
        "catatan": [
            "Diperlukan sebagai prasyarat untuk melangsungkan pernikahan di Dubai dan Emirat Utara",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap",
            "Harus ditandatangani pemohon langsung di depan petugas Konsuler KJRI Dubai"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- SK-003: Surat Keterangan Perceraian
-- --------------------------------------------------------------------------
(
    'SK-003',
    'Surat Keterangan Perceraian',
    '{
        "wajib": [
            "Salinan Akta Perceraian yang diterbitkan oleh Dubai Court atau Pengadilan Emirat Utara, dilegalisasi oleh MOFAIC UAE",
            "Salinan Akta Perkawinan",
            "Salinan paspor pemohon dan Visa Izin Tinggal (Residence Visa)",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [],
        "catatan": [
            "Merupakan bukti pencatatan perceraian WNI di Dubai dan Emirat Utara",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- SK-004: Surat Keterangan Kelahiran
-- --------------------------------------------------------------------------
(
    'SK-004',
    'Surat Keterangan Kelahiran',
    '{
        "wajib": [
            "Akta Kelahiran anak, asli dan salinannya",
            "Foto anak 4 lembar berwarna putih dan 4 lembar berwarna merah ukuran 4x6 cm",
            "Salinan paspor ayah dan ibu, serta Visa Izin Tinggal (Residence Visa) yang masih berlaku",
            "Akta nikah orang tua, asli dan salinannya, dilegalisasi oleh MOFAIC UAE",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [
            "NOC dari pihak suami atau istri untuk anak memiliki Kewarganegaraan Indonesia (untuk anak pemegang kewarganegaraan ganda)"
        ],
        "catatan": [
            "Diterbitkan untuk anak WNI maupun pemegang status warga negara ganda yang lahir di Dubai dan Emirat Utara",
            "Diperlukan untuk mendaftarkan kelahiran di Kantor Catatan Sipil di Indonesia",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- SK-005: Surat Keterangan Kematian
-- --------------------------------------------------------------------------
(
    'SK-005',
    'Surat Keterangan Kematian',
    '{
        "wajib": [
            "Salinan akta kematian yang diterbitkan oleh otoritas Pemerintah UAE",
            "Paspor asli almarhum / almarhumah",
            "Salinan kartu identitas almarhum / almarhumah"
        ],
        "kondisional": [],
        "catatan": [
            "Tidak dipungut biaya",
            "Merupakan bukti pencatatan kematian WNI di luar negeri",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    0.00,
    'Gratis'
),

-- --------------------------------------------------------------------------
-- SK-006: Surat Keterangan Jenazah / Abu Jenazah
-- --------------------------------------------------------------------------
(
    'SK-006',
    'Surat Keterangan Jenazah / Abu Jenazah',
    '{
        "wajib": [
            "Salinan akta kematian yang diterbitkan oleh otoritas Pemerintah UAE",
            "Paspor asli almarhum / almarhumah",
            "Salinan kartu identitas almarhum / almarhumah"
        ],
        "kondisional": [],
        "catatan": [
            "Tidak dipungut biaya",
            "Diperlukan untuk pengurusan jenazah atau abu jenazah yang akan dimakamkan di Indonesia",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    0.00,
    'Gratis'
),

-- --------------------------------------------------------------------------
-- SK-007: Surat Keterangan Pindah
-- --------------------------------------------------------------------------
(
    'SK-007',
    'Surat Keterangan Pindah',
    '{
        "wajib": [
            "Daftar barang pindahan dari perusahaan pemindah",
            "Salinan paspor asli dan Visa Izin Tinggal (Residence Visa) yang masih berlaku",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [],
        "catatan": [
            "Diberikan kepada WNI yang pindah dan berdiam di luar negeri paling singkat 1 tahun secara terus-menerus",
            "Digunakan untuk pembebasan Bea Masuk atas impor barang pindahan (dasar: PMK No. 28/PMK.04/2008)",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- SK-008: Surat Keterangan Terjemahan SIM Indonesia
-- --------------------------------------------------------------------------
(
    'SK-008',
    'Surat Keterangan Terjemahan SIM Indonesia',
    '{
        "wajib": [
            "SIM asli Indonesia yang masih berlaku (untuk pengajuan dan akan dikembalikan saat pengambilan)",
            "Salinan SIM Indonesia yang masih berlaku",
            "Salinan paspor asli dan Visa Izin Tinggal (Residence Visa) yang masih berlaku",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [],
        "catatan": [
            "Digunakan untuk pengurusan SIM di Dubai dan Emirat Utara",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    75.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- SK-009: Surat Keterangan Nama
-- --------------------------------------------------------------------------
(
    'SK-009',
    'Surat Keterangan Nama',
    '{
        "wajib": [
            "Salinan paspor asli dan Visa Izin Tinggal (Residence Visa) yang masih berlaku",
            "Mengisi formulir pendaftaran surat keterangan di KJRI Dubai"
        ],
        "kondisional": [],
        "catatan": [
            "Menerangkan sistem penamaan yang lazim berlaku di Indonesia dan ketentuan mengenai perubahan nama",
            "Lazim dibutuhkan dalam proses pengurusan ke catatan sipil di Dubai dan Emirat Utara",
            "Waktu proses 2 hari kerja setelah berkas diterima lengkap"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- SK-010: Surat Affidavit (Kewarganegaraan Ganda Anak)
-- --------------------------------------------------------------------------
(
    'SK-010',
    'Surat Affidavit (Pernyataan Kewarganegaraan Ganda Anak)',
    '{
        "wajib": [
            "Fotokopi paspor kedua orang tua",
            "Fotokopi Emirates ID kedua orang tua (dan visa bila ada)",
            "Fotokopi KTP / Kartu Keluarga (KK) / Surat keterangan domisili dari kedua orang tua (atau dari sisi orang tua WNI, apabila salah satu WNA)",
            "Surat nikah kedua orang tua yang sudah dilegalisir MOFAIC UAE",
            "Akta kelahiran anak yang sudah dilegalisir MOFAIC UAE",
            "Fotokopi Emirates ID anak",
            "Foto berlatar belakang merah 4 lembar",
            "Mengisi formulir permohonan dengan data lengkap"
        ],
        "kondisional": [
            "Surat pernyataan tidak berkeberatan dari orang tua WNA, ditandatangani di atas materai (apabila salah satu orang tua adalah WNA)",
            "Fotokopi paspor asing anak (bila ada)",
            "KTP anak (bila ada)"
        ],
        "catatan": [
            "Diperuntukkan bagi anak yang memiliki kewarganegaraan ganda Indonesia dan negara lain"
        ]
    }',
    105.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- SK-011: Surat Pengantar Pembuatan SIM UAE
-- --------------------------------------------------------------------------
(
    'SK-011',
    'Surat Pengantar Pembuatan SIM UAE',
    '{
        "wajib": [
            "SIM Indonesia asli",
            "Salinan berwarna SIM Indonesia",
            "NOC dari sponsor",
            "Salinan paspor",
            "Salinan Emirates ID"
        ],
        "kondisional": [],
        "catatan": [
            "Digunakan untuk pengurusan SIM di Dubai dan Emirat Utara"
        ]
    }',
    75.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- REG-001: Registrasi WNI Online (Lapor Diri)
-- --------------------------------------------------------------------------
(
    'REG-001',
    'Registrasi WNI Online (Lapor Diri)',
    '{
        "wajib": [
            "Buka link www.kjridubai.org",
            "Klik menu Layanan Konsuler, lalu pilih Daftar Diri",
            "Isi formulir dengan baik dan lengkap (biodata, nomor telepon di UAE dan di Indonesia)",
            "Verifikasi CAPTCHA pada formulir",
            "Klik Kirim Data Diri",
            "Screenshot atau foto Nama dan Nomor Registrasi yang muncul"
        ],
        "kondisional": [],
        "catatan": [
            "WNI yang sudah pernah datang ke KJRI Dubai dan pernah mengajukan layanan sebelumnya tidak perlu membuat nomor registrasi lagi",
            "Nomor registrasi wajib dimiliki sebelum mengajukan seluruh layanan konsuler"
        ]
    }',
    0.00,
    'Gratis'
),

-- --------------------------------------------------------------------------
-- REG-002: Pendaftaran PENDUL (Penduduk Luar Negeri / Lapor Diri Fisik)
-- --------------------------------------------------------------------------
(
    'REG-002',
    'Pendaftaran PENDUL (Penduduk Luar Negeri) / Lapor Diri',
    '{
        "wajib": [
            "Paspor asli",
            "Fotokopi paspor",
            "Fotokopi Emirates ID / Visa tinggal",
            "Fotokopi Kartu Tanda Penduduk (KTP) / Kartu Keluarga (KK)",
            "Surat keterangan bekerja / kontrak kerja dari Kementerian Tenaga Kerja UAE (Mohre) dengan gaji minimum AED 1.500",
            "Fotokopi paspor dan Emirates ID majikan / sponsor"
        ],
        "kondisional": [],
        "catatan": [
            "Pendaftaran PENDUL berfungsi sebagai pengganti surat cuti",
            "Wajib bagi WNI yang menetap dan bekerja di UAE"
        ]
    }',
    NULL,
    'Tidak ada biaya / belum ditentukan'
),

-- --------------------------------------------------------------------------
-- VIS-001: Single Visit Visa - Wisata (Tourism)
-- --------------------------------------------------------------------------
(
    'VIS-001',
    'Single Visit Visa Indonesia - Wisata (Tourism)',
    '{
        "wajib": [
            "Paspor asli dan salinan paspor yang masih berlaku minimal 6 bulan saat masuk ke Indonesia",
            "Salinan Residence Visa dan Emirates ID",
            "No Objection Certificate (NOC) dari employer / sponsor",
            "Tiket penerbangan dan reservasi hotel",
            "Rekening koran 3 bulan terakhir dengan saldo minimum USD 2.000 atau AED 8.000",
            "Foto 2 lembar (background putih)",
            "Health Protocol Statement Letter",
            "Financial Statement Letter"
        ],
        "kondisional": [],
        "catatan": [
            "Biaya AED 385 tunai",
            "Khusus untuk kunjungan wisata ke Indonesia"
        ]
    }',
    385.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- VIS-002: Single Visit Visa - Non-Wisata
-- --------------------------------------------------------------------------
(
    'VIS-002',
    'Single Visit Visa Indonesia - Non-Wisata (Bisnis / Keluarga / Lainnya)',
    '{
        "wajib": [
            "Paspor asli dan salinan paspor yang masih berlaku minimal 6 bulan saat masuk ke Indonesia",
            "Salinan Residence Visa dan Emirates ID",
            "No Objection Certificate (NOC) dari employer / sponsor",
            "Tiket penerbangan dan reservasi hotel",
            "Rekening koran 3 bulan terakhir dengan saldo minimum USD 2.000 atau AED 8.000",
            "Foto 2 lembar (background putih)",
            "Surat undangan resmi dari instansi di Indonesia",
            "Health Protocol Statement Letter",
            "Financial Statement Letter"
        ],
        "kondisional": [],
        "catatan": [
            "Biaya AED 510 tunai",
            "Untuk kunjungan non-wisata: bisnis, kunjungan keluarga, dll."
        ]
    }',
    510.00,
    'Tunai'
),

-- --------------------------------------------------------------------------
-- NIK-001: Nikah di KJRI Dubai - Wanita WNI Muslimah
-- --------------------------------------------------------------------------
(
    'NIK-001',
    'Pendaftaran Nikah di KJRI Dubai - Wanita WNI Muslimah',
    '{
        "wajib": [
            "Surat pengantar nikah dari KUA setempat model N1 s.d. N4, dilegalisir oleh Kemenkumham RI dan Kemenlu RI",
            "Copy paspor dan copy Visa Residence (atau copy Visa Kunjungan untuk non-residen)",
            "Copy KTP, Akta Lahir, Kartu Keluarga (KK), serta copy KTP / Paspor kedua orang tua",
            "Pas foto 4x6 dan 2x3 sebanyak 5 lembar (latar belakang biru)",
            "Hasil Pemeriksaan Kesehatan (General Medical Check Up) dan hasil PCR Tes"
        ],
        "kondisional": [
            "Surat Tawkil Wali dilegalisir Kemenkumham RI dan Kemenlu RI (jika wali wanita tidak dapat hadir dalam Akad Nikah)",
            "Akta cerai / putusan cerai / surat kematian suami (jika janda cerai atau janda ditinggal mati oleh suami)",
            "Surat Keterangan Tidak Keberatan / NOC dari majikan (jika pekerja rumah tangga / informal)"
        ],
        "catatan": [
            "Salah satu calon mempelai (pria atau wanita) harus residen UAE",
            "Akad Nikah dilangsungkan di KJRI Dubai paling cepat 10 hari kerja setelah pendaftaran, pada pukul 12.00-14.00",
            "KJRI Dubai akan mengumumkan rencana akad di papan pengumuman dan / atau media sosial KJRI Dubai",
            "KJRI Dubai berhak menolak permohonan jika persyaratan tidak dipenuhi dengan lengkap dan benar"
        ]
    }',
    200.00,
    'Tunai (belum termasuk biaya legalisasi Surat Nikah AED 95 per legalisasi)'
),

-- --------------------------------------------------------------------------
-- NIK-002: Nikah di KJRI Dubai - Pria WNI Muslim
-- --------------------------------------------------------------------------
(
    'NIK-002',
    'Pendaftaran Nikah di KJRI Dubai - Pria WNI Muslim',
    '{
        "wajib": [
            "Surat Keterangan Menikah model N1 s.d. N4 dari KUA setempat (salah satu dilegalisir Kemenkumham RI dan Kemenlu RI)",
            "Copy paspor dan copy Visa Residence (atau copy Visa Kunjungan)",
            "Surat keterangan bebas untuk menikah / Surat Single Status dari pihak berwenang, dilegalisir Kemenkumham RI dan Kemenlu RI",
            "Copy KTP, Akta Lahir, Kartu Keluarga (KK), serta copy KTP kedua orang tua",
            "Pas foto 4x6 dan 2x3 sebanyak 5 lembar (latar belakang biru)",
            "Hasil Pemeriksaan Kesehatan (General Medical Check Up) dan hasil PCR Tes"
        ],
        "kondisional": [
            "Akta cerai / putusan cerai dari Pengadilan Agama (jika duda)",
            "Surat izin poligami dari istri pertama di atas materai (jika sudah beristri)",
            "Surat izin poligami dari Pengadilan Agama Indonesia atau instansi berwenang (jika sudah beristri)"
        ],
        "catatan": [
            "Salah satu calon mempelai (pria atau wanita) harus residen UAE",
            "Akad Nikah dilangsungkan di KJRI Dubai paling cepat 10 hari kerja setelah pendaftaran, pada pukul 12.00-14.00",
            "KJRI Dubai berhak menolak permohonan jika persyaratan tidak dipenuhi dengan lengkap dan benar"
        ]
    }',
    200.00,
    'Tunai (belum termasuk biaya legalisasi Surat Nikah AED 95 per legalisasi)'
),

-- --------------------------------------------------------------------------
-- NIK-003: Nikah di KJRI Dubai - WNA Muslim
-- --------------------------------------------------------------------------
(
    'NIK-003',
    'Pendaftaran Nikah di KJRI Dubai - WNA Muslim',
    '{
        "wajib": [
            "Copy paspor dan copy visa izin tinggal di UAE",
            "Surat Keterangan Single Status / bebas untuk menikah dari negara asal, dilegalisir di Kedutaan / Konsulat UAE di negara asal dan dilegalisir MOFA UAE",
            "NOC dari Kedutaan / Konsulat Negara Asal di Abu Dhabi / Dubai, dilegalisir oleh MOFA UAE",
            "NOC dari Perusahaan",
            "Copy ID card / Copy Paspor kedua orang tua",
            "Pas foto 4x6 dan 2x3 sebanyak 5 lembar (latar belakang biru)",
            "Hasil Pemeriksaan Kesehatan (General Medical Check Up) dan hasil PCR Tes"
        ],
        "kondisional": [
            "Sertifikat Mualaf (bagi WNA yang baru masuk Islam)",
            "Surat Izin poligami dari Pengadilan / Mahkamah yang berwenang, dilegalisir MOFA UAE (jika sudah beristri)",
            "Surat izin dari istri pertama di atas materai, dilegalisir MOFA UAE (jika sudah beristri)",
            "NOC dari Majikan (jika pekerja rumah tangga / informal)"
        ],
        "catatan": [
            "Salah satu calon mempelai (pria atau wanita) harus residen UAE",
            "Akad Nikah dilangsungkan di KJRI Dubai paling cepat 10 hari kerja setelah pendaftaran, pada pukul 12.00-14.00",
            "KJRI Dubai berhak menolak permohonan jika persyaratan tidak dipenuhi dengan lengkap dan benar"
        ]
    }',
    200.00,
    'Tunai (belum termasuk biaya legalisasi Surat Nikah AED 95 per legalisasi)'
);

-- -----------------------------------------------------------------------------
-- Verifikasi
-- -----------------------------------------------------------------------------

-- Tampilkan semua layanan yang berhasil diinsert
SELECT
    id,
    kode_pelayanan,
    nama_pelayanan,
    biaya_aed,
    biaya_keterangan,
    jsonb_array_length(syarat -> 'wajib')        AS jumlah_syarat_wajib,
    jsonb_array_length(syarat -> 'kondisional')   AS jumlah_syarat_kondisional,
    jsonb_array_length(syarat -> 'catatan')       AS jumlah_catatan
FROM layanan_konsuler
ORDER BY id;
