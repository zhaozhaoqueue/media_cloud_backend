from datetime import datetime
from typing import List

from pydantic import BaseModel


class ShareCodeItem(BaseModel):
    id: str
    shareCode: str
    expireAt: datetime
    createdAt: datetime


class ShareCodeListData(BaseModel):
    list: List[ShareCodeItem]
    page: int
    pageSize: int
    total: int


class DeleteShareCodeData(BaseModel):
    ok: bool
