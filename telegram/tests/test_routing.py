from telegram.i18n import (
    LANGUAGE_LABELS,
    LANGUAGE_PROMPT,
    locale_from_language_label,
    locale_from_menu_label,
    parse_locale,
    t,
)
from telegram.routing import (
    language_keyboard,
    menu_keyboard,
    remove_keyboard,
    route_inbound_text,
    should_send_qr,
)


def test_start_always_shows_language_picker_and_clears_track():
    route = route_inbound_text("/start", "konsuler", "en")
    assert route.action == "show_language"
    assert route.track is None
    assert route.locale is None
    assert route.call_agent is False


def test_language_button_sets_locale_and_shows_menu():
    for label, locale in (
        (LANGUAGE_LABELS["id"], "id"),
        (LANGUAGE_LABELS["en"], "en"),
        (LANGUAGE_LABELS["ar"], "ar"),
    ):
        route = route_inbound_text(label, "janji_temu", None)
        assert route.action == "show_menu"
        assert route.track is None
        assert route.locale == locale
        assert route.call_agent is False


def test_kembali_with_locale_shows_menu_and_keeps_language():
    for label in (
        t("id", "menu_kembali"),
        t("en", "menu_kembali"),
        t("ar", "menu_kembali"),
    ):
        route = route_inbound_text(label, "janji_temu", "en")
        assert route.action == "show_menu"
        assert route.track is None
        assert route.locale is None
        assert route.call_agent is False


def test_kembali_without_locale_shows_language_picker():
    route = route_inbound_text(t("id", "menu_kembali"), "janji_temu", None)
    assert route.action == "show_language"
    assert route.track is None
    assert route.call_agent is False


def test_free_text_without_locale_shows_language_picker():
    route = route_inbound_text("halo", None, None)
    assert route.action == "show_language"
    assert route.track is None
    assert route.call_agent is False


def test_free_text_with_locale_keeps_current_track():
    route = route_inbound_text("syarat paspor pekerja formal", "konsuler", "id")
    assert route.action == "run_agent"
    assert route.track == "konsuler"
    assert route.locale is None
    assert route.call_agent is True


def test_english_and_arabic_booking_buttons_set_track():
    for label in (t("en", "menu_janji"), t("ar", "menu_janji")):
        route = route_inbound_text(label, None, "en")
        assert route.action == "run_agent"
        assert route.track == "janji_temu"
        assert route.locale is None
        assert route.call_agent is True


def test_english_and_arabic_konsuler_buttons_set_track():
    for label in (t("en", "menu_konsuler"), t("ar", "menu_konsuler")):
        route = route_inbound_text(label, None, "ar")
        assert route.action == "run_agent"
        assert route.track == "konsuler"
        assert route.call_agent is True


def test_indonesian_menu_without_locale_infers_id_and_enters_track():
    janji = route_inbound_text(t("id", "menu_janji"), None, None)
    assert janji.action == "run_agent"
    assert janji.track == "janji_temu"
    assert janji.locale == "id"
    assert janji.call_agent is True

    konsuler = route_inbound_text(t("id", "menu_konsuler"), None, None)
    assert konsuler.action == "run_agent"
    assert konsuler.track == "konsuler"
    assert konsuler.locale == "id"
    assert konsuler.call_agent is True


def test_language_keyboard_is_not_the_service_menu():
    language_labels = [
        button["text"] for row in language_keyboard()["keyboard"] for button in row
    ]
    assert language_labels == [
        LANGUAGE_LABELS["id"],
        LANGUAGE_LABELS["en"],
        LANGUAGE_LABELS["ar"],
    ]
    assert language_keyboard()["resize_keyboard"] is True
    assert language_keyboard()["one_time_keyboard"] is True
    assert language_keyboard()["is_persistent"] is False
    assert t("id", "menu_janji") not in language_labels
    assert LANGUAGE_PROMPT


def test_menu_keyboard_follows_locale():
    id_labels = [button["text"] for row in menu_keyboard("id")["keyboard"] for button in row]
    en_labels = [button["text"] for row in menu_keyboard("en")["keyboard"] for button in row]
    ar_labels = [button["text"] for row in menu_keyboard("ar")["keyboard"] for button in row]
    assert id_labels == [
        t("id", "menu_konsuler"),
        t("id", "menu_janji"),
        t("id", "menu_kembali"),
    ]
    assert en_labels == [
        t("en", "menu_konsuler"),
        t("en", "menu_janji"),
        t("en", "menu_kembali"),
    ]
    assert ar_labels == [
        t("ar", "menu_konsuler"),
        t("ar", "menu_janji"),
        t("ar", "menu_kembali"),
    ]
    assert id_labels != en_labels
    assert menu_keyboard("id")["resize_keyboard"] is True
    assert menu_keyboard("id")["one_time_keyboard"] is True
    assert menu_keyboard("id")["is_persistent"] is False
    assert remove_keyboard() == {"remove_keyboard": True}


def test_start_with_bot_suffix_still_shows_language_picker():
    route = route_inbound_text("/start@temujanji_bot", None, "id")
    assert route.action == "show_language"
    assert route.call_agent is False


def test_t_falls_back_to_indonesian_and_formats_qr():
    assert t(None, "error") == t("id", "error")
    caption = t("en", "qr_caption", code="KJRI-1", url="https://x")
    assert "KJRI-1" in caption
    assert "https://x" in caption
    assert locale_from_language_label("English") == "en"
    assert locale_from_menu_label(t("ar", "menu_janji")) == "ar"
    assert parse_locale("ar") == "ar"
    assert parse_locale("de") is None


def test_qr_only_for_janji_temu_with_payload():
    payload = {"qr_payload": "signed", "booking_code": "KJRI-1", "magic_url": "https://x"}
    assert should_send_qr("janji_temu", payload) is True
    assert should_send_qr("konsuler", payload) is False
    assert should_send_qr("janji_temu", None) is False
    assert should_send_qr(None, payload) is False
