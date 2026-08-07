import base64
import hashlib
import hmac
import json


def make_qr_payload(booking_code: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode(), booking_code.encode(), hashlib.sha256
    ).hexdigest()[:16]
    raw = json.dumps({"c": booking_code, "s": signature}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()


def verify_qr_payload(payload: str, secret: str) -> str | None:
    try:
        padding = "=" * (-len(payload) % 4)
        decoded = base64.b64decode(payload + padding, altchars=b"-_", validate=True)
        value = json.loads(decoded)
        booking_code = value["c"]
        signature = value["s"]
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return None

    if not isinstance(booking_code, str) or not isinstance(signature, str):
        return None
    expected_signature = hmac.new(
        secret.encode(), booking_code.encode(), hashlib.sha256
    ).hexdigest()[:16]
    if not hmac.compare_digest(signature, expected_signature):
        return None
    return booking_code
