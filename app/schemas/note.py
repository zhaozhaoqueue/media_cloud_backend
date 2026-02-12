from datetime import datetime
from typing import List

from pydantic import BaseModel


class NoteListItem(BaseModel):
    id: str
    title: str
    memberCount: int
    itemCount: int
    createdAt: datetime
    updatedAt: datetime


class NoteListData(BaseModel):
    list: List[NoteListItem]
    page: int
    pageSize: int
    total: int


class CreateNoteRequest(BaseModel):
    title: str


class CreateNoteData(BaseModel):
    id: str
    title: str
    createdAt: datetime
    updatedAt: datetime


class UpdateNoteRequest(BaseModel):
    title: str


class NoteDetailData(BaseModel):
    id: str
    title: str
    memberCount: int
    itemCount: int
    createdAt: datetime
    updatedAt: datetime


class CreateNoteShareCodeRequest(BaseModel):
    expiresIn: int
    maxUses: int | None = None


class NoteShareCodeData(BaseModel):
    shareCode: str
    expireAt: datetime


class JoinNoteRequest(BaseModel):
    shareCode: str


class JoinNoteData(BaseModel):
    noteId: str
    role: str


class NoteItemUser(BaseModel):
    id: str
    name: str
    avatar: str | None = None


class NoteItemData(BaseModel):
    id: str
    noteId: str
    content: str
    createdBy: NoteItemUser
    updatedBy: NoteItemUser
    createdAt: datetime
    updatedAt: datetime


class NoteItemListData(BaseModel):
    list: List[NoteItemData]
    page: int
    pageSize: int
    total: int


class CreateNoteItemRequest(BaseModel):
    content: str


class UpdateNoteItemRequest(BaseModel):
    content: str
