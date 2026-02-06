from datetime import datetime
from typing import List

from pydantic import BaseModel


class FileItem(BaseModel):
    id: str
    spaceId: str
    name: str
    mimeType: str
    size: int
    status: str
    finalUrl: str
    createdAt: datetime


class FileListData(BaseModel):
    list: List[FileItem]
    page: int
    pageSize: int
    total: int


class FileDetailData(BaseModel):
    id: str
    spaceId: str
    name: str
    mimeType: str
    size: int
    status: str
    finalUrl: str
    createdAt: datetime


class UploadCompleteData(BaseModel):
    ok: bool


class DeleteFileData(BaseModel):
    ok: bool


class UpdateFileRequest(BaseModel):
    name: str | None = None
