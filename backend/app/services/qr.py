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
