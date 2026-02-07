from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac


def _build_signature_payload(file_id: str, variant: str, expires: int) -> str:
    return f"{file_id}:{variant}:{expires}"


def sign_file_read_url(file_id: str, variant: str, expires: int, secret: str) -> str:
    payload = _build_signature_payload(file_id=file_id, variant=variant, expires=expires)
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_file_read_signature(
    file_id: str,
    variant: str,
    expires: int,
    signature: str,
    secret: str,
) -> bool:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if expires < now_ts:
        return False

    expected = sign_file_read_url(
        file_id=file_id,
        variant=variant,
        expires=expires,
        secret=secret,
    )
    return hmac.compare_digest(expected, signature)


def generate_signed_file_read_url(
    *,
    base_url: str,
    file_id: str,
    variant: str,
    ttl_seconds: int,
    secret: str,
) -> str:
    expires = int(datetime.now(timezone.utc).timestamp()) + ttl_seconds
    sig = sign_file_read_url(
        file_id=file_id,
        variant=variant,
        expires=expires,
        secret=secret,
    )
    return f"{base_url.rstrip('/')}/api/v1/files/{file_id}/{variant}?expires={expires}&sig={sig}"
