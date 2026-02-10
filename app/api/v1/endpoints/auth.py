import uuid
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.user_identity import UserIdentity
from app.schemas.auth import LoginData, LoginRequest, UserInfo
from app.schemas.common import Response
from app.services.jwt_tokens import create_access_token
from app.services.provider_identity import ProviderIdentity, resolve_provider_identity

router = APIRouter()
LOGIN_INVITE_CODE = "MC_BETA_2026"


def _load_identity(
    db: Session,
    *,
    provider: str,
    openid: str,
) -> UserIdentity | None:
    return db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == provider,
            UserIdentity.openid == openid,
        )
    ).scalar_one_or_none()


def _resolve_identity_from_login_payload(provider: str, code: str) -> ProviderIdentity:
    return resolve_provider_identity(provider=provider, code=code)


def _generate_new_user_name() -> str:
    suffix = secrets.token_hex(3)
    return f"User_{suffix}"


def _issue_token_and_user(user: User) -> Response[LoginData]:
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


@router.post("/auth/login", response_model=Response[LoginData])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Response[LoginData]:
    provider_identity = _resolve_identity_from_login_payload(
        provider=payload.provider,
        code=payload.code,
    )

    identity = _load_identity(
        db=db,
        provider=provider_identity.provider,
        openid=provider_identity.openid,
    )
    if identity:
        if provider_identity.unionid and identity.unionid != provider_identity.unionid:
            identity.unionid = provider_identity.unionid
            db.commit()

        user = db.get(User, identity.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return _issue_token_and_user(user)

    if (
        provider_identity.provider == "wechat_mini"
        and payload.inviteCode != LOGIN_INVITE_CODE
    ):
        raise HTTPException(status_code=403, detail="Invalid invite code")

    user = User(
        id=uuid.uuid4(),
        name=_generate_new_user_name(),
        avatar_url=None,
    )
    db.add(user)
    db.flush()

    new_identity = UserIdentity(
        user_id=user.id,
        provider=provider_identity.provider,
        openid=provider_identity.openid,
        unionid=provider_identity.unionid,
    )
    db.add(new_identity)
    db.commit()

    return _issue_token_and_user(user)
