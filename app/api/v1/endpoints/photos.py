from datetime import datetime
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.core.database import get_db
from app.models.file import File
from app.models.photo import Photo
from app.models.space import Space
from app.models.space_member import SpaceMember
from app.models.user import User
from app.schemas.common import Response
from app.schemas.member import OkData
from app.schemas.photo import (
    BatchCreatePhotosData,
    BatchCreatePhotosRequest,
    BatchDeletePhotosData,
    BatchDeletePhotosRequest,
    CreatePhotoData,
    CreatePhotoRequest,
    DownloadData,
    PhotoDetailData,
    PhotoListData,
    PhotoListItem,
    UpdatePhotoRequest,
    UploadTokenData,
    UploadTokenRequest,
    UploadItem,
)
from app.services.image import generate_thumbnail
from app.services.read_url import generate_signed_file_read_url
from app.services.storage import generate_upload_plan

router = APIRouter()
SPACE_MANAGER_ROLES = {"owner", "admin"}


def _parse_uuid(value: uuid.UUID | str, field_name: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def _get_space_member(
    db: Session,
    space_id: uuid.UUID | str,
    user_id: uuid.UUID,
) -> SpaceMember | None:
    space_uuid = _parse_uuid(space_id, "spaceId")
    return db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_uuid,
            SpaceMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def _require_space_member(
    db: Session,
    space_id: uuid.UUID | str,
    user_id: uuid.UUID,
) -> SpaceMember:
    member = _get_space_member(db=db, space_id=space_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=403, detail="Forbidden: not a member of this space")
    return member


def _require_photo_write_access(db: Session, photo: Photo, user_id: uuid.UUID) -> None:
    member = _require_space_member(db=db, space_id=photo.space_id, user_id=user_id)
    if photo.owner_id == user_id:
        return

    if member.role not in SPACE_MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: insufficient role")


def _set_space_cover_if_empty(db: Session, space_id: uuid.UUID, cover_url: str) -> None:
    db.execute(
        update(Space)
        .where(Space.id == space_id)
        .where(Space.cover_url.is_(None))
        .values(cover_url=cover_url)
    )


def _reassign_space_cover_on_photo_delete(db: Session, photo: Photo) -> None:
    space = db.get(Space, photo.space_id)
    if not space or space.cover_url not in {photo.url, photo.thumb_url}:
        return

    next_cover_url = db.execute(
        select(Photo.thumb_url)
        .where(Photo.space_id == photo.space_id)
        .where(Photo.id != photo.id)
        .order_by(Photo.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    space.cover_url = next_cover_url


def _prepare_photo_record(
    db: Session,
    *,
    space_id: str,
    file_id: str,
    name: str,
    owner_id: uuid.UUID,
) -> tuple[Photo, File]:
    file_uuid = _parse_uuid(file_id, "fileId")
    space_uuid = _parse_uuid(space_id, "spaceId")

    file = db.get(File, file_uuid)
    if not file:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    if file.status != "uploaded":
        raise HTTPException(status_code=400, detail=f"File not uploaded: {file_id}")
    if file.space_id != space_uuid:
        raise HTTPException(status_code=400, detail=f"File not in space: {file_id}")

    thumb_url = f"{settings.storage_base_url}/api/v1/files/{file.id}/thumb"
    photo = Photo(
        space_id=file.space_id,
        file_id=file.id,
        owner_id=owner_id,
        name=name,
        url=file.final_url,
        thumb_url=thumb_url,
        size=file.size,
    )
    db.add(photo)

    file.status = "used"
    _set_space_cover_if_empty(db=db, space_id=file.space_id, cover_url=photo.thumb_url)
    return photo, file


@router.get("/spaces/{space_id}/photos", response_model=Response[PhotoListData])
def list_photos(
    space_id: str,
    page: int = 1,
    pageSize: int = 30,
    order: str = "desc",
    ownerId: str | None = None,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[PhotoListData]:
    space_uuid = _parse_uuid(space_id, "spaceId")
    _require_space_member(db=db, space_id=space_uuid, user_id=user_id)

    offset = (page - 1) * pageSize

    base_filter = Photo.space_id == space_uuid
    if ownerId:
        owner_uuid = _parse_uuid(ownerId, "ownerId")
        base_filter = base_filter & (Photo.owner_id == owner_uuid)

    total = db.execute(
        select(func.count()).select_from(select(Photo.id).where(base_filter).subquery())
    ).scalar_one()

    stmt = select(Photo, User.name).join(User, User.id == Photo.owner_id).where(base_filter)
    if order.lower() == "asc":
        stmt = stmt.order_by(Photo.created_at.asc())
    else:
        stmt = stmt.order_by(Photo.created_at.desc())
    stmt = stmt.offset(offset).limit(pageSize)
    rows = db.execute(stmt).all()

    items = [
        PhotoListItem(
            id=str(photo.id),
            name=photo.name,
            thumbUrl=generate_signed_file_read_url(
                base_url=settings.storage_base_url,
                file_id=str(photo.file_id),
                variant="thumb",
                ttl_seconds=settings.read_url_ttl_seconds,
                secret=settings.read_url_signing_secret,
            ),
            ownerName=owner_name,
            createdAt=photo.created_at,
        )
        for photo, owner_name in rows
    ]

    return Response(
        data=PhotoListData(list=items, page=page, pageSize=pageSize, total=total)
    )


@router.get("/photos/{photo_id}", response_model=Response[PhotoDetailData])
def get_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[PhotoDetailData]:
    photo_uuid = _parse_uuid(photo_id, "photoId")
    stmt = (
        select(Photo, User.name)
        .join(User, User.id == Photo.owner_id)
        .where(Photo.id == photo_uuid)
    )
    row = db.execute(stmt).first()
    if not row:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo, owner_name = row
    _require_space_member(db=db, space_id=photo.space_id, user_id=user_id)

    return Response(
        data=PhotoDetailData(
            id=str(photo.id),
            name=photo.name,
            url=photo.url,
            ownerName=owner_name,
            createdAt=photo.created_at,
            size=photo.size,
            width=photo.width,
            height=photo.height,
            thumbUrl=photo.thumb_url,
        )
    )


@router.post("/photos/upload-token", response_model=Response[UploadTokenData])
def create_upload_token(
    payload: UploadTokenRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[UploadTokenData]:
    _require_space_member(db=db, space_id=payload.spaceId, user_id=user_id)

    uploads: list[UploadItem] = []

    for item in payload.files:
        file_id = uuid.uuid4()
        storage_key = f"files/{file_id}"
        plan = generate_upload_plan(settings.upload_token_ttl_seconds)
        upload_url = f"{settings.storage_base_url}/api/v1/uploads/{file_id}?token={plan.token}"
        final_url = f"{settings.storage_base_url}/api/v1/files/{file_id}/raw"

        record = File(
            id=file_id,
            space_id=payload.spaceId,
            uploader_id=user_id,
            name=item.name,
            mime_type=item.type,
            size=item.size,
            storage_key=storage_key,
            final_url=final_url,
            status="pending",
            upload_token=plan.token,
            upload_expires_at=plan.expires_at,
        )
        db.add(record)

        uploads.append(
            UploadItem(
                fileId=str(file_id),
                uploadUrl=upload_url,
                method="PUT",
                headers={"Content-Type": item.type},
                finalUrl=final_url,
            )
        )

    db.commit()

    return Response(data=UploadTokenData(uploads=uploads))


@router.post("/photos", response_model=Response[CreatePhotoData])
def create_photo(
    payload: CreatePhotoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[CreatePhotoData]:
    _require_space_member(db=db, space_id=payload.spaceId, user_id=user_id)
    photo, file = _prepare_photo_record(
        db=db,
        space_id=payload.spaceId,
        file_id=payload.fileId,
        name=payload.name,
        owner_id=user_id,
    )
    db.commit()

    background_tasks.add_task(
        generate_thumbnail,
        settings.storage_local_root,
        file.storage_key,
        f"thumbs/{file.id}.jpg",
        (settings.thumb_max_size, settings.thumb_max_size),
    )

    return Response(data=CreatePhotoData(id=str(photo.id), url=photo.url))


@router.post("/photos/batch", response_model=Response[BatchCreatePhotosData])
def create_photos_batch(
    payload: BatchCreatePhotosRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[BatchCreatePhotosData]:
    _require_space_member(db=db, space_id=payload.spaceId, user_id=user_id)

    ids: list[str] = []

    for item in payload.items:
        photo, file = _prepare_photo_record(
            db=db,
            space_id=payload.spaceId,
            file_id=item.fileId,
            name=item.name,
            owner_id=user_id,
        )
        ids.append(str(photo.id))

        background_tasks.add_task(
            generate_thumbnail,
            settings.storage_local_root,
            file.storage_key,
            f"thumbs/{file.id}.jpg",
            (settings.thumb_max_size, settings.thumb_max_size),
        )

    db.commit()

    return Response(data=BatchCreatePhotosData(ids=ids))


@router.get("/photos/{photo_id}/download", response_model=Response[DownloadData])
def download_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[DownloadData]:
    photo_uuid = _parse_uuid(photo_id, "photoId")
    photo = db.get(Photo, photo_uuid)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _require_space_member(db=db, space_id=photo.space_id, user_id=user_id)

    return Response(data=DownloadData(downloadUrl=photo.url))


@router.patch("/photos/{photo_id}", response_model=Response[PhotoDetailData])
def update_photo(
    photo_id: str,
    payload: UpdatePhotoRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[PhotoDetailData]:
    photo_uuid = _parse_uuid(photo_id, "photoId")
    photo = db.get(Photo, photo_uuid)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _require_photo_write_access(db=db, photo=photo, user_id=user_id)

    photo.name = payload.name
    db.commit()

    owner_name = db.execute(select(User.name).where(User.id == photo.owner_id)).scalar_one()
    return Response(
        data=PhotoDetailData(
            id=str(photo.id),
            name=photo.name,
            url=photo.url,
            ownerName=owner_name,
            createdAt=photo.created_at,
            size=photo.size,
            width=photo.width,
            height=photo.height,
            thumbUrl=photo.thumb_url,
        )
    )


@router.delete("/photos/{photo_id}", response_model=Response[OkData])
def delete_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    photo_uuid = _parse_uuid(photo_id, "photoId")
    photo = db.get(Photo, photo_uuid)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _require_photo_write_access(db=db, photo=photo, user_id=user_id)

    _reassign_space_cover_on_photo_delete(db=db, photo=photo)
    db.delete(photo)
    db.commit()

    return Response(data=OkData(ok=True))


@router.post("/photos/batch-delete", response_model=Response[BatchDeletePhotosData])
def delete_photos_batch(
    payload: BatchDeletePhotosRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[BatchDeletePhotosData]:
    dedup_ids = list(dict.fromkeys(payload.ids))
    if not dedup_ids:
        raise HTTPException(status_code=400, detail="ids must not be empty")

    parsed_ids = [_parse_uuid(photo_id, "photoId") for photo_id in dedup_ids]
    photos = db.execute(select(Photo).where(Photo.id.in_(parsed_ids))).scalars().all()
    photo_map = {str(photo.id): photo for photo in photos}

    missing_ids = [photo_id for photo_id in dedup_ids if photo_id not in photo_map]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Photos not found: {', '.join(missing_ids)}")

    for photo_id in dedup_ids:
        _require_photo_write_access(db=db, photo=photo_map[photo_id], user_id=user_id)

    for photo_id in dedup_ids:
        photo = photo_map[photo_id]
        _reassign_space_cover_on_photo_delete(db=db, photo=photo)
        db.delete(photo)

    db.commit()

    return Response(data=BatchDeletePhotosData(ok=True, ids=dedup_ids))
