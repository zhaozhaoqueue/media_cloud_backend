from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import secrets


@dataclass
class UploadPlan:
    token: str
    expires_at: datetime


def generate_upload_plan(ttl_seconds: int) -> UploadPlan:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    return UploadPlan(token=token, expires_at=expires_at)


def ensure_local_path(root: str, storage_key: str) -> Path:
    path = Path(root) / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
