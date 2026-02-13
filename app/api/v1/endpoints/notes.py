from datetime import datetime, timedelta, timezone
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.note import Note
from app.models.note_item import NoteItem
from app.models.note_member import NoteMember
from app.models.note_share_code import NoteShareCode
from app.models.user import User
from app.schemas.common import Response
from app.schemas.member import OkData
from app.schemas.note import (
    CreateNoteData,
    CreateNoteItemRequest,
    CreateNoteRequest,
    CreateNoteShareCodeRequest,
    JoinNoteData,
    JoinNoteRequest,
    NoteDetailData,
    NoteItemData,
    NoteItemListData,
    NoteItemUser,
    NoteListData,
    NoteListItem,
    NoteShareCodeData,
    UpdateNoteItemRequest,
    UpdateNoteRequest,
)

router = APIRouter()
NOTE_MANAGER_ROLES = {"owner", "admin"}


def _parse_uuid(value: uuid.UUID | str, field_name: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def _get_note_or_404(db: Session, note_id: uuid.UUID) -> Note:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def _get_note_member(db: Session, *, note_id: uuid.UUID, user_id: uuid.UUID) -> NoteMember | None:
    return db.execute(
        select(NoteMember).where(
            NoteMember.note_id == note_id,
            NoteMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def _require_note_member(db: Session, *, note_id: uuid.UUID, user_id: uuid.UUID) -> NoteMember:
    member = _get_note_member(db=db, note_id=note_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=403, detail="Forbidden: not a member of this note")
    return member


def _require_note_manager(db: Session, *, note_id: uuid.UUID, user_id: uuid.UUID) -> NoteMember:
    member = _require_note_member(db=db, note_id=note_id, user_id=user_id)
    if member.role not in NOTE_MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
    return member


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="title must not be empty")
    return normalized


def _normalize_content(content: str) -> str:
    normalized = content.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="content must not be empty")
    return normalized


def _build_note_detail_data(db: Session, note: Note) -> NoteDetailData:
    member_count = db.execute(
        select(func.count()).select_from(NoteMember).where(NoteMember.note_id == note.id)
    ).scalar_one()
    item_count = db.execute(
        select(func.count()).select_from(NoteItem).where(NoteItem.note_id == note.id)
    ).scalar_one()

    return NoteDetailData(
        id=str(note.id),
        title=note.title,
        memberCount=member_count,
        itemCount=item_count,
        createdAt=note.created_at,
        updatedAt=note.updated_at,
    )


def _to_note_item_user(user: User) -> NoteItemUser:
    return NoteItemUser(id=str(user.id), name=user.name)


def _to_note_item_data(item: NoteItem, created_user: User, updated_user: User) -> NoteItemData:
    return NoteItemData(
        id=str(item.id),
        noteId=str(item.note_id),
        content=item.content,
        createdBy=_to_note_item_user(created_user),
        updatedBy=_to_note_item_user(updated_user),
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


def _load_note_item_with_users(
    db: Session,
    *,
    note_id: uuid.UUID,
    item_id: uuid.UUID,
) -> tuple[NoteItem, User, User] | None:
    created_user = aliased(User)
    updated_user = aliased(User)

    row = db.execute(
        select(NoteItem, created_user, updated_user)
        .join(created_user, created_user.id == NoteItem.created_by)
        .join(updated_user, updated_user.id == NoteItem.updated_by)
        .where(NoteItem.note_id == note_id, NoteItem.id == item_id)
    ).first()

    if not row:
        return None

    return row[0], row[1], row[2]


@router.get("/notes", response_model=Response[NoteListData])
def list_notes(
    page: int = 1,
    pageSize: int = 20,
    order: str = "desc",
    title: str | None = None,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteListData]:
    offset = (page - 1) * pageSize

    note_ids_stmt = select(NoteMember.note_id).where(NoteMember.user_id == user_id)
    filtered_notes_stmt = select(Note.id).where(Note.id.in_(note_ids_stmt))
    if title:
        filtered_notes_stmt = filtered_notes_stmt.where(Note.title.ilike(f"%{title}%"))

    total = db.execute(select(func.count()).select_from(filtered_notes_stmt.subquery())).scalar_one()

    member_counts = (
        select(NoteMember.note_id, func.count().label("member_count"))
        .group_by(NoteMember.note_id)
        .subquery()
    )
    item_counts = (
        select(NoteItem.note_id, func.count().label("item_count"))
        .group_by(NoteItem.note_id)
        .subquery()
    )

    stmt = select(
        Note,
        func.coalesce(member_counts.c.member_count, 0).label("member_count"),
        func.coalesce(item_counts.c.item_count, 0).label("item_count"),
    ).outerjoin(member_counts, member_counts.c.note_id == Note.id).outerjoin(
        item_counts, item_counts.c.note_id == Note.id
    )

    stmt = stmt.where(Note.id.in_(filtered_notes_stmt))

    if order.lower() == "asc":
        stmt = stmt.order_by(Note.updated_at.asc())
    else:
        stmt = stmt.order_by(Note.updated_at.desc())

    stmt = stmt.offset(offset).limit(pageSize)

    rows = db.execute(stmt).all()
    items = [
        NoteListItem(
            id=str(note.id),
            title=note.title,
            memberCount=member_count,
            itemCount=item_count,
            createdAt=note.created_at,
            updatedAt=note.updated_at,
        )
        for note, member_count, item_count in rows
    ]

    return Response(data=NoteListData(list=items, page=page, pageSize=pageSize, total=total))


@router.post("/notes", response_model=Response[CreateNoteData])
def create_note(
    payload: CreateNoteRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[CreateNoteData]:
    now = datetime.now(timezone.utc)
    note = Note(
        title=_normalize_title(payload.title),
        owner_id=user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.flush()

    member = NoteMember(note_id=note.id, user_id=user_id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(note)

    return Response(
        data=CreateNoteData(
            id=str(note.id),
            title=note.title,
            createdAt=note.created_at,
            updatedAt=note.updated_at,
        )
    )


@router.get("/notes/{note_id}", response_model=Response[NoteDetailData])
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteDetailData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    note = _get_note_or_404(db, note_uuid)
    _require_note_member(db=db, note_id=note_uuid, user_id=user_id)

    return Response(data=_build_note_detail_data(db=db, note=note))


@router.patch("/notes/{note_id}", response_model=Response[NoteDetailData])
def update_note(
    note_id: str,
    payload: UpdateNoteRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteDetailData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    note = _get_note_or_404(db, note_uuid)
    _require_note_manager(db=db, note_id=note_uuid, user_id=user_id)

    note.title = _normalize_title(payload.title)
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)

    return Response(data=_build_note_detail_data(db=db, note=note))


@router.delete("/notes/{note_id}", response_model=Response[OkData])
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    note = _get_note_or_404(db, note_uuid)
    _require_note_manager(db=db, note_id=note_uuid, user_id=user_id)

    db.execute(delete(NoteItem).where(NoteItem.note_id == note_uuid))
    db.delete(note)
    db.commit()

    return Response(data=OkData(ok=True))


@router.post("/notes/{note_id}/share-code", response_model=Response[NoteShareCodeData])
def create_note_share_code(
    note_id: str,
    payload: CreateNoteShareCodeRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteShareCodeData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    _get_note_or_404(db, note_uuid)
    _require_note_manager(db=db, note_id=note_uuid, user_id=user_id)

    if payload.expiresIn <= 0:
        raise HTTPException(status_code=400, detail="expiresIn must be greater than 0")
    if payload.maxUses is not None and payload.maxUses <= 0:
        raise HTTPException(status_code=400, detail="maxUses must be greater than 0")

    code = secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:6]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload.expiresIn)

    record = NoteShareCode(
        note_id=note_uuid,
        share_code=code,
        expires_at=expires_at,
        created_by=user_id,
        max_uses=payload.maxUses,
        used_count=0,
    )
    db.add(record)
    db.commit()

    return Response(data=NoteShareCodeData(shareCode=code, expireAt=expires_at))


@router.post("/notes/join", response_model=Response[JoinNoteData])
def join_note(
    payload: JoinNoteRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[JoinNoteData]:
    share = db.execute(
        select(NoteShareCode).where(NoteShareCode.share_code == payload.shareCode)
    ).scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Share code not found")

    if share.revoked_at is not None:
        raise HTTPException(status_code=400, detail="Share code revoked")

    now = datetime.now(timezone.utc)
    expires_at = share.expires_at if share.expires_at.tzinfo else share.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=400, detail="Share code expired")

    if share.max_uses is not None and share.used_count >= share.max_uses:
        raise HTTPException(status_code=400, detail="Share code exhausted")

    existing = _get_note_member(db=db, note_id=share.note_id, user_id=user_id)
    if existing:
        return Response(data=JoinNoteData(noteId=str(share.note_id), role=existing.role))

    member = NoteMember(note_id=share.note_id, user_id=user_id, role="member")
    db.add(member)
    share.used_count += 1
    db.commit()

    return Response(data=JoinNoteData(noteId=str(share.note_id), role="member"))


@router.get("/notes/{note_id}/items", response_model=Response[NoteItemListData])
def list_note_items(
    note_id: str,
    page: int = 1,
    pageSize: int = 50,
    order: str = "desc",
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteItemListData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    _get_note_or_404(db, note_uuid)
    _require_note_member(db=db, note_id=note_uuid, user_id=user_id)

    offset = (page - 1) * pageSize

    total = db.execute(
        select(func.count()).select_from(select(NoteItem.id).where(NoteItem.note_id == note_uuid).subquery())
    ).scalar_one()

    created_user = aliased(User)
    updated_user = aliased(User)
    stmt = (
        select(NoteItem, created_user, updated_user)
        .join(created_user, created_user.id == NoteItem.created_by)
        .join(updated_user, updated_user.id == NoteItem.updated_by)
        .where(NoteItem.note_id == note_uuid)
    )

    if order.lower() == "asc":
        stmt = stmt.order_by(NoteItem.updated_at.asc())
    else:
        stmt = stmt.order_by(NoteItem.updated_at.desc())

    rows = db.execute(stmt.offset(offset).limit(pageSize)).all()
    items = [_to_note_item_data(item, creator, updater) for item, creator, updater in rows]

    return Response(data=NoteItemListData(list=items, page=page, pageSize=pageSize, total=total))


@router.post("/notes/{note_id}/items", response_model=Response[NoteItemData])
def create_note_item(
    note_id: str,
    payload: CreateNoteItemRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteItemData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    note = _get_note_or_404(db, note_uuid)
    _require_note_member(db=db, note_id=note_uuid, user_id=user_id)

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    item = NoteItem(
        note_id=note_uuid,
        content=_normalize_content(payload.content),
        created_by=user_id,
        updated_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(item)

    note.updated_at = now
    db.commit()
    db.refresh(item)

    return Response(data=_to_note_item_data(item, user, user))


@router.get("/notes/{note_id}/items/{item_id}", response_model=Response[NoteItemData])
def get_note_item(
    note_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteItemData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    item_uuid = _parse_uuid(item_id, "itemId")

    _get_note_or_404(db, note_uuid)
    _require_note_member(db=db, note_id=note_uuid, user_id=user_id)

    row = _load_note_item_with_users(db=db, note_id=note_uuid, item_id=item_uuid)
    if not row:
        raise HTTPException(status_code=404, detail="Note item not found")

    item, created_user, updated_user = row
    return Response(data=_to_note_item_data(item, created_user, updated_user))


@router.patch("/notes/{note_id}/items/{item_id}", response_model=Response[NoteItemData])
def update_note_item(
    note_id: str,
    item_id: str,
    payload: UpdateNoteItemRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[NoteItemData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    item_uuid = _parse_uuid(item_id, "itemId")

    note = _get_note_or_404(db, note_uuid)
    _require_note_member(db=db, note_id=note_uuid, user_id=user_id)

    row = _load_note_item_with_users(db=db, note_id=note_uuid, item_id=item_uuid)
    if not row:
        raise HTTPException(status_code=404, detail="Note item not found")

    item, created_user, _ = row
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    item.content = _normalize_content(payload.content)
    item.updated_by = user_id
    item.updated_at = now
    note.updated_at = now
    db.commit()
    db.refresh(item)

    return Response(data=_to_note_item_data(item, created_user, user))


@router.delete("/notes/{note_id}/items/{item_id}", response_model=Response[OkData])
def delete_note_item(
    note_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    note_uuid = _parse_uuid(note_id, "noteId")
    item_uuid = _parse_uuid(item_id, "itemId")

    note = _get_note_or_404(db, note_uuid)
    _require_note_member(db=db, note_id=note_uuid, user_id=user_id)

    item = db.get(NoteItem, item_uuid)
    if not item or item.note_id != note_uuid:
        raise HTTPException(status_code=404, detail="Note item not found")

    db.delete(item)
    note.updated_at = datetime.now(timezone.utc)
    db.commit()

    return Response(data=OkData(ok=True))
