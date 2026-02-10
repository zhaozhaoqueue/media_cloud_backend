import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import UpdateUserProfileRequest, UserInfo
from app.schemas.common import Response

router = APIRouter()


@router.patch("/users/me", response_model=Response[UserInfo])
def update_me(
    payload: UpdateUserProfileRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[UserInfo]:
    if payload.name is None and payload.avatar is None:
        raise HTTPException(status_code=400, detail="name or avatar is required")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        normalized = payload.name.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="name must not be empty")
        user.name = normalized
    if payload.avatar is not None:
        user.avatar_url = payload.avatar

    db.commit()

    return Response(data=UserInfo(id=str(user.id), name=user.name, avatar=user.avatar_url))
