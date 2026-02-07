import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.space import Space
from app.models.space_member import SpaceMember
from app.models.user import User
from app.schemas.common import Response
from app.schemas.member import (
    AddMemberRequest,
    MemberItem,
    MemberListData,
    OkData,
    TransferOwnerRequest,
    UpdateMemberRoleRequest,
)

router = APIRouter()
MANAGEABLE_ROLES = {"member", "admin"}


def _parse_uuid(value: uuid.UUID | str, field_name: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def _get_space_or_404(db: Session, space_id: uuid.UUID) -> Space:
    space = db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


def _get_space_member(
    db: Session,
    *,
    space_id: uuid.UUID,
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
    *,
    space_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    member = _get_space_member(db=db, space_id=space_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=403, detail="Forbidden: not a member of this space")


def _require_space_owner(space: Space, current_user_id: uuid.UUID) -> None:
    if space.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: owner required")


@router.get("/spaces/{space_id}/members", response_model=Response[MemberListData])
def list_members(
    space_id: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[MemberListData]:
    space_uuid = _parse_uuid(space_id, "spaceId")
    _get_space_or_404(db=db, space_id=space_uuid)
    _require_space_member(db=db, space_id=space_uuid, user_id=user_id)

    stmt = (
        select(User.id, User.name, SpaceMember.role)
        .join(SpaceMember, SpaceMember.user_id == User.id)
        .where(SpaceMember.space_id == space_uuid)
    )
    rows = db.execute(stmt).all()
    items = [MemberItem(userId=str(r.id), name=r.name, role=r.role) for r in rows]

    return Response(data=MemberListData(list=items))


@router.post("/spaces/{space_id}/members", response_model=Response[OkData])
def add_member(
    space_id: str,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    space_uuid = _parse_uuid(space_id, "spaceId")
    target_user_id = _parse_uuid(payload.userId, "userId")
    space = _get_space_or_404(db=db, space_id=space_uuid)
    _require_space_owner(space=space, current_user_id=current_user_id)

    if payload.role not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=400, detail="role must be one of: member, admin")

    target_user = db.get(User, target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_uuid, SpaceMember.user_id == target_user_id
        )
    ).scalar_one_or_none()
    if existing:
        return Response(data=OkData(ok=True))

    member = SpaceMember(space_id=space_uuid, user_id=target_user_id, role=payload.role)
    db.add(member)
    db.commit()

    return Response(data=OkData(ok=True))


@router.post(
    "/spaces/{space_id}/members/{user_id}/role", response_model=Response[OkData]
)
def update_member_role(
    space_id: str,
    user_id: str,
    payload: UpdateMemberRoleRequest,
    db: Session = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    space_uuid = _parse_uuid(space_id, "spaceId")
    target_user_id = _parse_uuid(user_id, "userId")
    space = _get_space_or_404(db=db, space_id=space_uuid)
    _require_space_owner(space=space, current_user_id=current_user_id)

    if payload.role not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=400, detail="role must be one of: member, admin")
    if target_user_id == space.owner_id:
        raise HTTPException(status_code=400, detail="Cannot change owner role directly")

    member = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_uuid, SpaceMember.user_id == target_user_id
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.role = payload.role
    db.commit()

    return Response(data=OkData(ok=True))


@router.delete(
    "/spaces/{space_id}/members/{user_id}", response_model=Response[OkData]
)
def remove_member(
    space_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    space_uuid = _parse_uuid(space_id, "spaceId")
    target_user_id = _parse_uuid(user_id, "userId")
    space = _get_space_or_404(db=db, space_id=space_uuid)
    _require_space_owner(space=space, current_user_id=current_user_id)

    if target_user_id == space.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove current owner")

    member = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_uuid, SpaceMember.user_id == target_user_id
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()

    return Response(data=OkData(ok=True))


@router.post("/spaces/{space_id}/owner/transfer", response_model=Response[OkData])
def transfer_space_owner(
    space_id: str,
    payload: TransferOwnerRequest,
    db: Session = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response[OkData]:
    space_uuid = _parse_uuid(space_id, "spaceId")
    new_owner_user_id = _parse_uuid(payload.newOwnerUserId, "newOwnerUserId")
    space = _get_space_or_404(db=db, space_id=space_uuid)
    _require_space_owner(space=space, current_user_id=current_user_id)

    if new_owner_user_id == current_user_id:
        return Response(data=OkData(ok=True))
    if payload.previousOwnerRole not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=400, detail="previousOwnerRole must be member or admin")

    new_owner_member = _get_space_member(db=db, space_id=space_uuid, user_id=new_owner_user_id)
    if not new_owner_member:
        raise HTTPException(status_code=404, detail="New owner must already be a member")

    current_owner_member = _get_space_member(
        db=db,
        space_id=space_uuid,
        user_id=current_user_id,
    )
    if not current_owner_member:
        raise HTTPException(status_code=500, detail="Owner membership data missing")

    current_owner_member.role = payload.previousOwnerRole
    new_owner_member.role = "owner"
    space.owner_id = new_owner_user_id
    db.commit()

    return Response(data=OkData(ok=True))
