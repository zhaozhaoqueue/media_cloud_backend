from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.core.database import get_db
from app.models.file import File
from app.schemas.common import Response
from app.schemas.file import (
    DeleteFileData,
    FileDetailData,
    FileListData,
    FileItem,
    UpdateFileRequest,
    UploadCompleteData,
)
from app.services.read_url import verify_file_read_signature
from app.services.storage import ensure_local_path

router = APIRouter()


def _authorize_file_read(
    *,
    file_id: str,
    variant: str,
    expires: int | None,
    sig: str | None,
    authorization: str | None,
) -> None:
    # Signed URL access for mini-program image loading.
    if expires is not None or sig is not None:
        if expires is None or sig is None:
            raise HTTPException(status_code=403, detail="Invalid signed url")
        is_valid = verify_file_read_signature(
            file_id=file_id,
            variant=variant,
            expires=expires,
            signature=sig,
            secret=settings.read_url_signing_secret,
        )
        if not is_valid:
            raise HTTPException(status_code=403, detail="Invalid or expired signed url")
        return

    # Token auth path.
    get_current_user_id(authorization=authorization)


@router.get("/files", response_model=Response[FileListData])
def list_files(
    spaceId: str = Query(...),
    page: int = 1,
    pageSize: int = 30,
    order: str = "desc",
    status: str | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[FileListData]:
    offset = (page - 1) * pageSize

    base_filter = File.space_id == spaceId
    if status:
        base_filter = base_filter & (File.status == status)

    total = db.execute(
        select(func.count()).select_from(select(File.id).where(base_filter).subquery())
    ).scalar_one()

    stmt = select(File).where(base_filter)
    if order.lower() == "asc":
        stmt = stmt.order_by(File.created_at.asc())
    else:
        stmt = stmt.order_by(File.created_at.desc())
    stmt = stmt.offset(offset).limit(pageSize)
    files = db.execute(stmt).scalars().all()

    items = [
        FileItem(
            id=str(item.id),
            spaceId=str(item.space_id) if item.space_id else None,
            name=item.name,
            mimeType=item.mime_type,
            size=item.size,
            status=item.status,
            finalUrl=item.final_url,
            createdAt=item.created_at,
        )
        for item in files
    ]

    return Response(data=FileListData(list=items, page=page, pageSize=pageSize, total=total))


@router.get("/files/{file_id}", response_model=Response[FileDetailData])
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[FileDetailData]:
    record = db.get(File, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        data=FileDetailData(
            id=str(record.id),
            spaceId=str(record.space_id) if record.space_id else None,
            name=record.name,
            mimeType=record.mime_type,
            size=record.size,
            status=record.status,
            finalUrl=record.final_url,
            createdAt=record.created_at,
        )
    )


@router.put("/uploads/{file_id}", response_model=Response[UploadCompleteData])
async def upload_file(
    file_id: str,
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> Response[UploadCompleteData]:
    record = db.get(File, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if not record.upload_token or record.upload_token != token:
        raise HTTPException(status_code=403, detail="Invalid upload token")
    if record.upload_expires_at:
        expires_at = (
            record.upload_expires_at
            if record.upload_expires_at.tzinfo is not None
            else record.upload_expires_at.replace(tzinfo=timezone.utc)
        )
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Upload token expired")

    storage_path = ensure_local_path(settings.storage_local_root, record.storage_key)

    with storage_path.open("wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    record.status = "uploaded"
    db.commit()

    return Response(data=UploadCompleteData(ok=True))


@router.get("/files/{file_id}/raw")
def download_raw_file(
    file_id: str,
    expires: int | None = None,
    sig: str | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    _authorize_file_read(
        file_id=file_id,
        variant="raw",
        expires=expires,
        sig=sig,
        authorization=authorization,
    )

    record = db.get(File, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    path = Path(settings.storage_local_root) / record.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(path, media_type=record.mime_type, filename=record.name)


@router.get("/files/{file_id}/thumb")
def download_thumb_file(
    file_id: str,
    expires: int | None = None,
    sig: str | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    _authorize_file_read(
        file_id=file_id,
        variant="thumb",
        expires=expires,
        sig=sig,
        authorization=authorization,
    )

    record = db.get(File, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    path = Path(settings.storage_local_root) / f"thumbs/{file_id}.jpg"
    if not path.exists():
        raw_path = Path(settings.storage_local_root) / record.storage_key
        if not raw_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail missing")
        return FileResponse(raw_path, media_type=record.mime_type, filename=record.name)

    return FileResponse(path, media_type="image/jpeg", filename=f"{file_id}.jpg")


@router.delete("/files/{file_id}", response_model=Response[DeleteFileData])
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[DeleteFileData]:
    record = db.get(File, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(record)
    db.commit()

    return Response(data=DeleteFileData(ok=True))


@router.patch("/files/{file_id}", response_model=Response[FileDetailData])
def update_file(
    file_id: str,
    payload: UpdateFileRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[FileDetailData]:
    record = db.get(File, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if payload.name is not None:
        record.name = payload.name

    db.commit()

    return Response(
        data=FileDetailData(
            id=str(record.id),
            spaceId=str(record.space_id) if record.space_id else None,
            name=record.name,
            mimeType=record.mime_type,
            size=record.size,
            status=record.status,
            finalUrl=record.final_url,
            createdAt=record.created_at,
        )
    )
