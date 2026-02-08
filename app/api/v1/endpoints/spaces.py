from datetime import datetime, timedelta, timezone
import secrets
import re
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.core.database import get_db
from app.models.space import Space
from app.models.photo import Photo
from app.models.space_member import SpaceMember
from app.models.space_share_code import SpaceShareCode
from app.schemas.common import Response
from app.schemas.member import OkData
from app.schemas.space import (
    CreateSpaceData,
    CreateSpaceRequest,
    JoinSpaceData,
    JoinSpaceRequest,
    ShareCodeData,
    ShareCodeRequest,
    SpaceDetailData,
    SpaceListData,
    SpaceListItem,
    UpdateSpaceRequest,
)
from app.services.read_url import generate_signed_file_read_url

router = APIRouter()
SPACE_MANAGER_ROLES = {"owner", "admin"}
THUMB_PATH_PATTERN = re.compile(r"^/api/v1/files/([0-9a-fA-F-]{36})/thumb$")


def _get_space_or_404(db: Session, space_id: str) -> Space:
    space = db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


def _get_space_member(
    db: Session,
    space_id: str,
    user_id: uuid.UUID,
) -> SpaceMember | None:
    return db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id,
            SpaceMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def _require_space_member(
    db: Session,
    space_id: str,
    user_id: uuid.UUID,
) -> SpaceMember:
    member = _get_space_member(db=db, space_id=space_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=403, detail="Forbidden: not a member of this space")
    return member


def _require_space_manager(
    db: Session,
    space_id: str,
    user_id: uuid.UUID,
) -> SpaceMember:
    member = _require_space_member(db=db, space_id=space_id, user_id=user_id)
    if member.role not in SPACE_MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
    return member


def _to_signed_cover_url(cover_url: str | None) -> str | None:
    if not cover_url:
        return None

    parsed = urlparse(cover_url)
    path = parsed.path if parsed.scheme else cover_url.split("?", 1)[0]
    match = THUMB_PATH_PATTERN.match(path)
    if not match:
        return cover_url

    file_id = match.group(1)
    try:
        uuid.UUID(file_id)
    except ValueError:
        return cover_url

    return generate_signed_file_read_url(
        base_url=settings.storage_base_url,
        file_id=file_id,
        variant="thumb",
        ttl_seconds=settings.read_url_ttl_seconds,
        secret=settings.read_url_signing_secret,
    )


@router.get("/spaces", response_model=Response[SpaceListData])
def list_spaces(
    page: int = 1,
    pageSize: int = 20,
    order: str = "desc",
    name: str | None = None,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[SpaceListData]:
    offset = (page - 1) * pageSize

    space_ids_stmt = select(SpaceMember.space_id).where(SpaceMember.user_id == user_id)
    filtered_spaces_stmt = select(Space.id).where(Space.id.in_(space_ids_stmt))
    if name:
        filtered_spaces_stmt = filtered_spaces_stmt.where(Space.name.ilike(f"%{name}%"))

    total = db.execute(
        select(func.count()).select_from(filtered_spaces_stmt.subquery())
    ).scalar_one()

    member_counts = (
        select(SpaceMember.space_id, func.count().label("member_count"))
        .group_by(SpaceMember.space_id)
        .subquery()
    )
    photo_counts = (
        select(Photo.space_id, func.count().label("photo_count"))
        .group_by(Photo.space_id)
        .subquery()
    )

    stmt = select(
        Space,
        func.coalesce(member_counts.c.member_count, 0).label("member_count"),
        func.coalesce(photo_counts.c.photo_count, 0).label("photo_count"),
    ).outerjoin(member_counts, member_counts.c.space_id == Space.id).outerjoin(
        photo_counts, photo_counts.c.space_id == Space.id
    )

    stmt = stmt.where(Space.id.in_(filtered_spaces_stmt))

    if order.lower() == "asc":
        stmt = stmt.order_by(Space.created_at.asc())
    else:
        stmt = stmt.order_by(Space.created_at.desc())

    stmt = stmt.offset(offset).limit(pageSize)

    rows = db.execute(stmt).all()

    items = [
        SpaceListItem(
            id=str(space.id),
            name=space.name,
            memberCount=member_count,
            photoCount=photo_count,
            coverUrl=_to_signed_cover_url(space.cover_url),
        )
        for space, member_count, photo_count in rows
    ]

    return Response(
        data=SpaceListData(list=items, page=page, pageSize=pageSize, total=total)
    )


@router.post("/spaces", response_model=Response[CreateSpaceData])
def create_space(
    payload: CreateSpaceRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[CreateSpaceData]:
    space = Space(name=payload.name, owner_id=user_id)
    db.add(space)
    db.flush()

    member = SpaceMember(space_id=space.id, user_id=user_id, role="owner")
    db.add(member)
    db.commit()

    return Response(data=CreateSpaceData(id=str(space.id), name=space.name))


@router.get("/spaces/{space_id}", response_model=Response[SpaceDetailData])
def get_space(
    space_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[SpaceDetailData]:
    space = _get_space_or_404(db, space_id)
    _require_space_member(db=db, space_id=space_id, user_id=user_id)

    member_count = db.execute(
        select(func.count()).select_from(SpaceMember).where(SpaceMember.space_id == space_id)
    ).scalar_one()
    photo_count = db.execute(
        select(func.count()).select_from(Photo).where(Photo.space_id == space_id)
    ).scalar_one()

    return Response(
        data=SpaceDetailData(
            id=str(space.id),
            name=space.name,
            memberCount=member_count,
            photoCount=photo_count,
            coverUrl=_to_signed_cover_url(space.cover_url),
        )
    )


@router.patch("/spaces/{space_id}", response_model=Response[SpaceDetailData])
def update_space(
    space_id: str,
    payload: UpdateSpaceRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[SpaceDetailData]:
    space = _get_space_or_404(db, space_id)
    _require_space_manager(db=db, space_id=space_id, user_id=user_id)

    if payload.name is not None:
        space.name = payload.name
    if payload.coverUrl is not None:
        space.cover_url = payload.coverUrl

    db.commit()

    member_count = db.execute(
        select(func.count()).select_from(SpaceMember).where(SpaceMember.space_id == space_id)
    ).scalar_one()
    photo_count = db.execute(
        select(func.count()).select_from(Photo).where(Photo.space_id == space_id)
    ).scalar_one()

    return Response(
        data=SpaceDetailData(
            id=str(space.id),
            name=space.name,
            memberCount=member_count,
            photoCount=photo_count,
            coverUrl=_to_signed_cover_url(space.cover_url),
        )
    )


@router.delete("/spaces/{space_id}", response_model=Response[OkData])
def delete_space(
    space_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    space = _get_space_or_404(db, space_id)
    _require_space_manager(db=db, space_id=space_id, user_id=user_id)

    db.delete(space)
    db.commit()

    return Response(data=OkData(ok=True))


@router.post("/spaces/{space_id}/share-code", response_model=Response[ShareCodeData])
def create_share_code(
    space_id: str,
    payload: ShareCodeRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[ShareCodeData]:
    if payload.expiresIn <= 0:
        raise HTTPException(status_code=400, detail="expiresIn must be greater than 0")

    space = _get_space_or_404(db, space_id)
    _require_space_manager(db=db, space_id=space_id, user_id=user_id)

    code = secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:6]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload.expiresIn)

    record = SpaceShareCode(
        space_id=space.id,
        share_code=code,
        expires_at=expires_at,
        created_by=user_id,
    )
    db.add(record)
    db.commit()

    return Response(data=ShareCodeData(shareCode=code, expireAt=expires_at))


@router.post("/spaces/join", response_model=Response[JoinSpaceData])
def join_space(
    payload: JoinSpaceRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[JoinSpaceData]:
    share = db.execute(
        select(SpaceShareCode).where(SpaceShareCode.share_code == payload.shareCode)
    ).scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Share code not found")
    now = datetime.now(timezone.utc)
    expires_at = (
        share.expires_at
        if share.expires_at.tzinfo is not None
        else share.expires_at.replace(tzinfo=timezone.utc)
    )
    if expires_at < now:
        raise HTTPException(status_code=400, detail="Share code expired")

    existing = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == share.space_id, SpaceMember.user_id == user_id
        )
    ).scalar_one_or_none()
    role = "member"
    if not existing:
        member = SpaceMember(space_id=share.space_id, user_id=user_id, role="member")
        db.add(member)
        db.commit()
    else:
        role = existing.role

    return Response(data=JoinSpaceData(spaceId=str(share.space_id), role=role))
