"""Shared instruction lock so ADK agents follow session.state.locale."""

LOCALE_INSTRUCTION = """
Locale sesi saat ini: {locale}
Balas HANYA dalam bahasa {locale}:
- id → Bahasa Indonesia
- en → English
- ar → العربية
Jika {locale} adalah en, wajib English. Jika ar, wajib العربية.
Jangan fallback ke Bahasa Indonesia kecuali {locale} kosong atau id.
Jangan mencampur bahasa. Terjemahkan error tool dan teks syarat/DB ke bahasa pengguna.
Kode booking, kode layanan, tanggal ISO, dan ID tetap utuh.
"""
