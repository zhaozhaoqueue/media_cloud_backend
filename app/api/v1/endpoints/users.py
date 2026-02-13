import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.core.database import get_db
from app.models.file import File
from app.models.user import User
from app.schemas.auth import (
    AvatarUploadTokenData,
    AvatarUploadTokenRequest,
    UpdateUserProfileRequest,
    UserInfo,
)
from app.schemas.common import Response
from app.services.storage import generate_upload_plan
from app.services.user_avatar import build_user_avatar_url

router = APIRouter()


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


@router.post("/users/me/avatar/upload-token", response_model=Response[AvatarUploadTokenData])
def create_avatar_upload_token(
    payload: AvatarUploadTokenRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[AvatarUploadTokenData]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.size <= 0:
        raise HTTPException(status_code=400, detail="size must be positive")
    if not payload.type.startswith("image/"):
        raise HTTPException(status_code=400, detail="avatar must be image/*")

    file_id = uuid.uuid4()
    storage_key = f"avatars/{user_id}/{file_id}"
    plan = generate_upload_plan(settings.upload_token_ttl_seconds)
    upload_url = f"{settings.storage_base_url}/api/v1/uploads/{file_id}?token={plan.token}"
    final_url = f"{settings.storage_base_url}/api/v1/files/{file_id}/raw"

    record = File(
        id=file_id,
        space_id=None,
        uploader_id=user_id,
        name=payload.name,
        mime_type=payload.type,
        size=payload.size,
        storage_key=storage_key,
        final_url=final_url,
        status="pending",
        upload_token=plan.token,
        upload_expires_at=plan.expires_at,
    )
    db.add(record)
    db.commit()

    return Response(
        data=AvatarUploadTokenData(
            fileId=str(file_id),
            uploadUrl=upload_url,
            method="PUT",
            headers={"Content-Type": payload.type},
            finalUrl=final_url,
        )
    )


@router.patch("/users/me", response_model=Response[UserInfo])
def update_me(
    payload: UpdateUserProfileRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[UserInfo]:
    if payload.name is None and payload.avatarFileId is None:
        raise HTTPException(status_code=400, detail="name or avatarFileId is required")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        normalized = payload.name.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="name must not be empty")
        user.name = normalized
    if payload.avatarFileId is not None:
        avatar_file_id = _parse_uuid(payload.avatarFileId, "avatarFileId")
        avatar_file = db.get(File, avatar_file_id)
        if not avatar_file:
            raise HTTPException(status_code=404, detail="Avatar file not found")
        if avatar_file.uploader_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden: not uploader of avatar file")
        if avatar_file.space_id is not None:
            raise HTTPException(status_code=400, detail="avatarFileId must reference avatar upload")
        if avatar_file.status != "uploaded":
            raise HTTPException(status_code=400, detail="Avatar file not uploaded")

        avatar_file.status = "used"
        user.avatar_file_id = avatar_file.id
        user.avatar_url = None

    db.commit()

    return Response(
        data=UserInfo(
            id=str(user.id),
            name=user.name,
            avatar=build_user_avatar_url(user.avatar_file_id),
        )
    )
