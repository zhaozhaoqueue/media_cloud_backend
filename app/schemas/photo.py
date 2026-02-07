from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel


class PhotoListItem(BaseModel):
    id: str
    name: str
    thumbUrl: str
    ownerName: str
    createdAt: datetime


class PhotoListData(BaseModel):
    list: List[PhotoListItem]
    page: int
    pageSize: int
    total: int


class PhotoDetailData(BaseModel):
    id: str
    name: str
    url: str
    ownerName: str
    createdAt: datetime
    size: int
    width: int | None = None
    height: int | None = None
    thumbUrl: str | None = None


class UploadFileItem(BaseModel):
    name: str
    size: int
    type: str


class UploadTokenRequest(BaseModel):
    spaceId: str
    files: List[UploadFileItem]


class UploadItem(BaseModel):
    fileId: str
    uploadUrl: str
    method: str
    headers: Dict[str, str]
    finalUrl: str


class UploadTokenData(BaseModel):
    uploads: List[UploadItem]


class CreatePhotoRequest(BaseModel):
    spaceId: str
    fileId: str
    name: str


class CreatePhotoData(BaseModel):
    id: str
    url: str


class UpdatePhotoRequest(BaseModel):
    name: str


class BatchPhotoItem(BaseModel):
    fileId: str
    name: str


class BatchCreatePhotosRequest(BaseModel):
    spaceId: str
    items: List[BatchPhotoItem]


class BatchCreatePhotosData(BaseModel):
    ids: List[str]


class DownloadData(BaseModel):
    downloadUrl: str


class BatchDeletePhotosRequest(BaseModel):
    ids: List[str]


class BatchDeletePhotosData(BaseModel):
    ok: bool
    ids: List[str]
