import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.user_identity import UserIdentity
from app.schemas.auth import LoginData, LoginRequest, UserInfo
from app.schemas.common import Response
from app.services.jwt_tokens import create_access_token

router = APIRouter()


def _resolve_display_name(nickname: str | None) -> str:
    if nickname is None:
        return "New User"
    trimmed = nickname.strip()
    return trimmed if trimmed else "New User"


@router.post("/auth/login", response_model=Response[LoginData])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Response[LoginData]:
    provider = "wechat_mini"
    openid = payload.code

    identity = db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == provider, UserIdentity.openid == openid
        )
    ).scalar_one_or_none()

    if identity:
        user = db.get(User, identity.user_id)
    else:
        user = User(
            id=uuid.uuid4(),
            name=_resolve_display_name(payload.nickname),
            avatar_url=payload.avatar,
        )
        db.add(user)
        db.flush()
        identity = UserIdentity(user_id=user.id, provider=provider, openid=openid)
        db.add(identity)
        db.commit()

    token = create_access_token(
        subject=str(user.id),
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=settings.jwt_expires_minutes,
    )
    return Response(
        data=LoginData(
            token=token,
            user=UserInfo(id=str(user.id), name=user.name, avatar=user.avatar_url),
        )
    )
