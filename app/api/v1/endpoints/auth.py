import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.user_identity import UserIdentity
from app.schemas.auth import LoginData, LoginRequest, RegisterRequest, UserInfo
from app.schemas.common import Response
from app.services.jwt_tokens import create_access_token
from app.services.provider_identity import ProviderIdentity, resolve_provider_identity

router = APIRouter()
# Internal beta gate: only clients with this fixed access code can log in.
REGISTRATION_ACCESS_CODE = "MC_BETA_2026"


def _resolve_display_name(nickname: str | None) -> str:
    if nickname is None:
        return "New User"
    trimmed = nickname.strip()
    return trimmed if trimmed else "New User"


def _validate_access_code(access_code: str) -> None:
    if access_code != REGISTRATION_ACCESS_CODE:
        raise HTTPException(status_code=403, detail="Invalid access code")


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


@router.post("/auth/register", response_model=Response[LoginData])
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> Response[LoginData]:
    _validate_access_code(payload.accessCode)
    provider_identity = _resolve_identity_from_login_payload(
        provider=payload.provider,
        code=payload.code,
    )

    identity = db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == provider_identity.provider,
            UserIdentity.openid == provider_identity.openid,
        )
    ).scalar_one_or_none()
    if identity:
        raise HTTPException(status_code=409, detail="Account already exists")

    user = User(
        id=uuid.uuid4(),
        name=_resolve_display_name(payload.nickname),
        avatar_url=payload.avatar,
    )
    db.add(user)
    db.flush()

    identity = UserIdentity(
        user_id=user.id,
        provider=provider_identity.provider,
        openid=provider_identity.openid,
        unionid=provider_identity.unionid,
    )
    db.add(identity)
    db.commit()

    return _issue_token_and_user(user)


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
    if not identity:
        raise HTTPException(status_code=404, detail="Account not found")

    if provider_identity.unionid and identity.unionid != provider_identity.unionid:
        identity.unionid = provider_identity.unionid
        db.commit()

    user = db.get(User, identity.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _issue_token_and_user(user)
