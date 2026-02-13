from __future__ import annotations

import uuid

from app.core.config import settings
from app.services.read_url import generate_signed_file_read_url


def build_user_avatar_url(avatar_file_id: uuid.UUID | str | None) -> str | None:
    if not avatar_file_id:
        return None

    return generate_signed_file_read_url(
        base_url=settings.storage_base_url,
        file_id=str(avatar_file_id),
        variant="raw",
        ttl_seconds=settings.read_url_ttl_seconds,
        secret=settings.read_url_signing_secret,
    )
