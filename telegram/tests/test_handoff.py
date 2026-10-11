from telegram.handoff import (
    can_create_bot_failure_handoff,
    detect_escalation_trigger,
    is_from_staff_group,
)


def test_detect_escalation_keywords():
    for text in (
        "saya mau bicara dengan agen manusia",
        "hubungi petugas",
        "operator dong",
        "minta tolong manusia",
        "bot ini tidak membantu",
    ):
        assert detect_escalation_trigger(text) is True


def test_detect_crisis_keywords():
    for text in (
        "saya disiksa majikan",
        "paspor ditahan majikan",
        "gaji tidak dibayar",
        "saya diancam dideportasi",
    ):
        assert detect_escalation_trigger(text) is True


def test_no_escalation_for_ordinary_question():
    for text in (
        "syarat perpanjang paspor apa ya",
        "berapa biaya legalisasi dokumen",
        "halo",
    ):
        assert detect_escalation_trigger(text) is False


def test_is_from_staff_group():
    assert is_from_staff_group("123", "123") is True
    assert is_from_staff_group("123", "456") is False
    assert is_from_staff_group("123", "") is False
    assert is_from_staff_group("123", "123") is True


def test_bot_failure_cooldown_dedupes_same_session(monkeypatch):
    monkeypatch.setenv("HANDOFF_BOT_FAILURE_COOLDOWN_SEC", "300")
    # Clear any in-process state from prior tests
    from telegram import handoff

    handoff._bot_failure_ts.clear()

    assert can_create_bot_failure_handoff("sess-a") is True
    assert can_create_bot_failure_handoff("sess-a") is False
    assert can_create_bot_failure_handoff("sess-b") is True
