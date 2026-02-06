from datetime import datetime
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.core.database import get_db
from app.models.file import File
from app.models.photo import Photo
from app.models.user import User
from app.schemas.common import Response
from app.schemas.member import OkData
from app.schemas.photo import (
    BatchCreatePhotosData,
    BatchCreatePhotosRequest,
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
from app.services.storage import generate_upload_plan

router = APIRouter()


@router.get("/spaces/{space_id}/photos", response_model=Response[PhotoListData])
def list_photos(
    space_id: str,
    page: int = 1,
    pageSize: int = 30,
    order: str = "desc",
    ownerId: str | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[PhotoListData]:
    offset = (page - 1) * pageSize

    base_filter = Photo.space_id == space_id
    if ownerId:
        base_filter = base_filter & (Photo.owner_id == ownerId)

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
            thumbUrl=photo.thumb_url,
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
    user_id: str = Depends(get_current_user_id),
) -> Response[PhotoDetailData]:
    stmt = (
        select(Photo, User.name)
        .join(User, User.id == Photo.owner_id)
        .where(Photo.id == photo_id)
    )
    row = db.execute(stmt).first()
    if not row:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo, owner_name = row
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
    user_id: str = Depends(get_current_user_id),
) -> Response[UploadTokenData]:
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
    user_id: str = Depends(get_current_user_id),
) -> Response[CreatePhotoData]:
    file = db.get(File, payload.fileId)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file.status != "uploaded":
        raise HTTPException(status_code=400, detail="File not uploaded yet")
    if str(file.space_id) != payload.spaceId:
        raise HTTPException(status_code=400, detail="File does not belong to space")

    thumb_url = f"{settings.storage_base_url}/api/v1/files/{file.id}/thumb"

    photo = Photo(
        space_id=payload.spaceId,
        file_id=file.id,
        owner_id=user_id,
        name=payload.name,
        url=file.final_url,
        thumb_url=thumb_url,
        size=file.size,
    )
    db.add(photo)

    file.status = "used"
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
    user_id: str = Depends(get_current_user_id),
) -> Response[BatchCreatePhotosData]:
    ids: list[str] = []

    for item in payload.items:
        file = db.get(File, item.fileId)
        if not file:
            raise HTTPException(status_code=404, detail=f"File not found: {item.fileId}")
        if file.status != "uploaded":
            raise HTTPException(status_code=400, detail=f"File not uploaded: {item.fileId}")
        if str(file.space_id) != payload.spaceId:
            raise HTTPException(status_code=400, detail=f"File not in space: {item.fileId}")

        thumb_url = f"{settings.storage_base_url}/api/v1/files/{file.id}/thumb"

        photo = Photo(
            space_id=payload.spaceId,
            file_id=file.id,
            owner_id=user_id,
            name=item.name,
            url=file.final_url,
            thumb_url=thumb_url,
            size=file.size,
        )
        db.add(photo)
        file.status = "used"
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
    user_id: str = Depends(get_current_user_id),
) -> Response[DownloadData]:
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return Response(data=DownloadData(downloadUrl=photo.url))


@router.patch("/photos/{photo_id}", response_model=Response[PhotoDetailData])
def update_photo(
    photo_id: str,
    payload: UpdatePhotoRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[PhotoDetailData]:
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

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
    user_id: str = Depends(get_current_user_id),
) -> Response[OkData]:
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    db.delete(photo)
    db.commit()

    return Response(data=OkData(ok=True))
