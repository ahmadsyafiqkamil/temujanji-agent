from telegram.routing import (
    MENU_JANJI,
    MENU_KEMBALI,
    MENU_KONSULER,
    menu_keyboard,
    route_inbound_text,
    should_send_qr,
)


def test_start_shows_menu_and_clears_track():
    route = route_inbound_text("/start", "konsuler")
    assert route.action == "show_menu"
    assert route.track is None
    assert route.call_agent is False


def test_kembali_shows_menu_and_clears_track():
    route = route_inbound_text(MENU_KEMBALI, "janji_temu")
    assert route.action == "show_menu"
    assert route.track is None
    assert route.call_agent is False


def test_konsuler_menu_sets_track_and_runs_agent():
    route = route_inbound_text(MENU_KONSULER, None)
    assert route.action == "run_agent"
    assert route.track == "konsuler"
    assert route.call_agent is True


def test_janji_temu_menu_sets_track_and_runs_agent():
    route = route_inbound_text(MENU_JANJI, None)
    assert route.action == "run_agent"
    assert route.track == "janji_temu"
    assert route.call_agent is True


def test_free_text_keeps_current_track():
    route = route_inbound_text("syarat paspor pekerja formal", "konsuler")
    assert route.action == "run_agent"
    assert route.track == "konsuler"
    assert route.call_agent is True


def test_keyboard_contains_both_menus_and_back():
    labels = [button["text"] for row in menu_keyboard()["keyboard"] for button in row]
    assert labels == [MENU_KONSULER, MENU_JANJI, MENU_KEMBALI]
    assert menu_keyboard()["resize_keyboard"] is True


def test_qr_only_for_janji_temu_with_payload():
    payload = {"qr_payload": "signed", "booking_code": "KJRI-1", "magic_url": "https://x"}
    assert should_send_qr("janji_temu", payload) is True
    assert should_send_qr("konsuler", payload) is False
    assert should_send_qr("janji_temu", None) is False
    assert should_send_qr(None, payload) is False
