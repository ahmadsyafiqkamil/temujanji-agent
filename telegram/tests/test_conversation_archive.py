from telegram.conversation_archive import detect_gratitude_closure


def test_detects_clean_farewell():
    for text in (
        "terima kasih",
        "makasih banyak ya",
        "thank you",
        "sampai jumpa",
        "sudah cukup, terima kasih",
    ):
        assert detect_gratitude_closure(text) == "gratitude"


def test_continuation_signals_are_not_closure():
    for text in (
        "terima kasih, tapi saya mau tanya lagi",
        "makasih, berapa biayanya?",
        "thank you, satu lagi bagaimana caranya",
    ):
        assert detect_gratitude_closure(text) is None


def test_non_gratitude_is_not_closure():
    for text in ("syarat paspor", "halo", "berapa biaya"):
        assert detect_gratitude_closure(text) is None
