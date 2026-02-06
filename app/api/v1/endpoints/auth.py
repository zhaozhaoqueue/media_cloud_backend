import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.user_identity import UserIdentity
from app.schemas.auth import LoginData, LoginRequest, UserInfo
from app.schemas.common import Response

router = APIRouter()


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
        user = User(id=uuid.uuid4(), name="New User")
        db.add(user)
        db.flush()
        identity = UserIdentity(user_id=user.id, provider=provider, openid=openid)
        db.add(identity)
        db.commit()

    token = "dev-token"
    return Response(
        data=LoginData(
            token=token,
            user=UserInfo(id=str(user.id), name=user.name, avatar=user.avatar_url),
        )
    )
