from telegram.i18n import STRINGS, Locale, t

NEW_KEYS = [
    "closure_reply",
    "handoff_confirmation",
    "handoff_queued",
    "bot_failure_cooldown",
]


def test_new_keys_present_in_all_locales():
    locales: list[Locale] = ["id", "en", "ar"]
    for locale in locales:
        for key in NEW_KEYS:
            assert key in STRINGS[locale], f"{key} missing in {locale}"
            assert STRINGS[locale][key].strip()


def test_handoff_confirmation_localized():
    assert t("id", "handoff_confirmation") != t("en", "handoff_confirmation")
    assert t("en", "handoff_confirmation") != t("ar", "handoff_confirmation")
