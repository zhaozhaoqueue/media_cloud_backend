import uuid

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> uuid.UUID:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required for dev auth")
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id") from exc


__all__ = ["get_db", "get_current_user_id", "Session"]
