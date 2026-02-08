import uuid

from fastapi import Header, HTTPException
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.jwt_tokens import decode_access_token


def get_current_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> uuid.UUID:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    try:
        payload = decode_access_token(
            token=token,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return uuid.UUID(subject)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id in token") from exc


__all__ = ["get_db", "get_current_user_id", "Session"]
