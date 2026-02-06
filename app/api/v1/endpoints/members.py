from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.space import Space
from app.models.space_member import SpaceMember
from app.models.user import User
from app.schemas.common import Response
from app.schemas.member import AddMemberRequest, MemberItem, MemberListData, OkData, UpdateMemberRoleRequest

router = APIRouter()


@router.get("/spaces/{space_id}/members", response_model=Response[MemberListData])
def list_members(
    space_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[MemberListData]:
    space = db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    stmt = (
        select(User.id, User.name, SpaceMember.role)
        .join(SpaceMember, SpaceMember.user_id == User.id)
        .where(SpaceMember.space_id == space_id)
    )
    rows = db.execute(stmt).all()
    items = [MemberItem(userId=str(r.id), name=r.name, role=r.role) for r in rows]

    return Response(data=MemberListData(list=items))


@router.post("/spaces/{space_id}/members", response_model=Response[OkData])
def add_member(
    space_id: str,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> Response[OkData]:
    existing = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == payload.userId
        )
    ).scalar_one_or_none()
    if existing:
        return Response(data=OkData(ok=True))

    member = SpaceMember(space_id=space_id, user_id=payload.userId, role=payload.role)
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
    current_user_id: str = Depends(get_current_user_id),
) -> Response[OkData]:
    member = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id
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
    current_user_id: str = Depends(get_current_user_id),
) -> Response[OkData]:
    member = db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()

    return Response(data=OkData(ok=True))
