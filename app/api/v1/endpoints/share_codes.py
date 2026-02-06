from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.space import Space
from app.models.space_share_code import SpaceShareCode
from app.schemas.common import Response
from app.schemas.share_code import DeleteShareCodeData, ShareCodeItem, ShareCodeListData

router = APIRouter()


@router.get("/spaces/{space_id}/share-codes", response_model=Response[ShareCodeListData])
def list_share_codes(
    space_id: str,
    page: int = 1,
    pageSize: int = 20,
    activeOnly: bool = False,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[ShareCodeListData]:
    space = db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    offset = (page - 1) * pageSize
    base_filter = SpaceShareCode.space_id == space_id
    if activeOnly:
        base_filter = base_filter & (SpaceShareCode.expires_at > func.now())

    total = db.execute(
        select(func.count()).select_from(select(SpaceShareCode.id).where(base_filter).subquery())
    ).scalar_one()

    stmt = (
        select(SpaceShareCode)
        .where(base_filter)
        .order_by(SpaceShareCode.created_at.desc())
        .offset(offset)
        .limit(pageSize)
    )
    rows = db.execute(stmt).scalars().all()

    items = [
        ShareCodeItem(
            id=str(row.id),
            shareCode=row.share_code,
            expireAt=row.expires_at,
            createdAt=row.created_at,
        )
        for row in rows
    ]

    return Response(
        data=ShareCodeListData(list=items, page=page, pageSize=pageSize, total=total)
    )


@router.delete(
    "/spaces/{space_id}/share-codes/{share_code_id}", response_model=Response[DeleteShareCodeData]
)
def delete_share_code(
    space_id: str,
    share_code_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response[DeleteShareCodeData]:
    record = db.get(SpaceShareCode, share_code_id)
    if not record or str(record.space_id) != space_id:
        raise HTTPException(status_code=404, detail="Share code not found")

    db.delete(record)
    db.commit()

    return Response(data=DeleteShareCodeData(ok=True))
