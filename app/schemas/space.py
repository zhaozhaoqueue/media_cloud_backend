from datetime import datetime
from typing import List

from pydantic import BaseModel


class SpaceListItem(BaseModel):
    id: str
    name: str
    memberCount: int
    photoCount: int
    coverUrl: str | None


class SpaceListData(BaseModel):
    list: List[SpaceListItem]
    page: int
    pageSize: int
    total: int


class CreateSpaceRequest(BaseModel):
    name: str


class CreateSpaceData(BaseModel):
    id: str
    name: str


class UpdateSpaceRequest(BaseModel):
    name: str | None = None
    coverUrl: str | None = None


class SpaceDetailData(BaseModel):
    id: str
    name: str
    memberCount: int
    photoCount: int
    coverUrl: str | None


class ShareCodeRequest(BaseModel):
    expiresIn: int


class ShareCodeData(BaseModel):
    shareCode: str
    expireAt: datetime


class JoinSpaceRequest(BaseModel):
    shareCode: str


class JoinSpaceData(BaseModel):
    spaceId: str
    role: str
