"""Telegram chrome strings and locale helpers. Not a translation framework."""

from __future__ import annotations

from typing import Literal

Locale = Literal["id", "en", "ar"]
MessageKey = Literal[
    "greeting",
    "menu_konsuler",
    "menu_janji",
    "menu_kembali",
    "error",
    "qr_caption",
]
MenuAction = Literal["konsuler", "janji_temu", "kembali"]

DEFAULT_LOCALE: Locale = "id"

LANGUAGE_LABELS: dict[Locale, str] = {
    "id": "Bahasa Indonesia",
    "en": "English",
    "ar": "العربية",
}

LANGUAGE_PROMPT = (
    "Pilih bahasa / Please choose a language / الرجاء اختيار اللغة"
)

STRINGS: dict[Locale, dict[MessageKey, str]] = {
    "id": {
        "greeting": (
            "Assalamualaikum / Selamat datang di layanan chatbot KJRI Dubai.\n\n"
            "Pilih menu:"
        ),
        "menu_konsuler": "Cek layanan kekonsuleran",
        "menu_janji": "Janji temu",
        "menu_kembali": "Kembali ke menu",
        "error": "Maaf, pesan Anda belum bisa diproses. Silakan coba lagi sebentar.",
        "qr_caption": (
            "Kode QR check-in untuk {code}\n"
            "Tunjukkan kode ini kepada petugas pada hari janji temu.\n"
            "Rincian: {url}"
        ),
    },
    "en": {
        "greeting": (
            "Assalamualaikum / Welcome to the KJRI Dubai chatbot.\n\n"
            "Choose a menu:"
        ),
        "menu_konsuler": "Check consular services",
        "menu_janji": "Book appointment",
        "menu_kembali": "Back to menu",
        "error": "Sorry, your message could not be processed. Please try again shortly.",
        "qr_caption": (
            "Check-in QR for {code}\n"
            "Show this code to staff on your appointment day.\n"
            "Details: {url}"
        ),
    },
    "ar": {
        "greeting": (
            "السلام عليكم / مرحباً بكم في خدمة الدردشة للقنصلية الإندونيسية في دبي.\n\n"
            "اختر القائمة:"
        ),
        "menu_konsuler": "تحقق من الخدمات القنصلية",
        "menu_janji": "حجز موعد",
        "menu_kembali": "العودة إلى القائمة",
        "error": "عذراً، تعذر معالجة رسالتك. يرجى المحاولة مرة أخرى بعد قليل.",
        "qr_caption": (
            "رمز QR للتسجيل لـ {code}\n"
            "أظهر هذا الرمز للموظف في يوم الموعد.\n"
            "التفاصيل: {url}"
        ),
    },
}


def parse_locale(value: object) -> Locale | None:
    if value == "id" or value == "en" or value == "ar":
        return value
    return None


def t(locale: Locale | None, key: MessageKey, **kwargs: object) -> str:
    resolved = parse_locale(locale) or DEFAULT_LOCALE
    template = STRINGS[resolved][key]
    if not kwargs:
        return template
    return template.format(**kwargs)


def locale_from_language_label(text: str) -> Locale | None:
    for locale, label in LANGUAGE_LABELS.items():
        if text == label:
            return locale
    return None


def locale_from_menu_label(text: str) -> Locale | None:
    for locale, strings in STRINGS.items():
        if text in {
            strings["menu_konsuler"],
            strings["menu_janji"],
            strings["menu_kembali"],
        }:
            return locale
    return None


def menu_action_from_label(text: str) -> MenuAction | None:
    for strings in STRINGS.values():
        if text == strings["menu_konsuler"]:
            return "konsuler"
        if text == strings["menu_janji"]:
            return "janji_temu"
        if text == strings["menu_kembali"]:
            return "kembali"
    return None


def all_menu_labels() -> frozenset[str]:
    labels: set[str] = set()
    for strings in STRINGS.values():
        labels.add(strings["menu_konsuler"])
        labels.add(strings["menu_janji"])
        labels.add(strings["menu_kembali"])
    return frozenset(labels)
