from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Optional


def verify_line_signature(body: bytes, signature: Optional[str], channel_secret: str) -> bool:
    if not signature or not channel_secret:
        return False

    digest = hmac.new(
        channel_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    expected_signature = base64.b64encode(digest).decode("utf-8")

    return hmac.compare_digest(expected_signature, signature)
