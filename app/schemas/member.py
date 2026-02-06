from typing import List

from pydantic import BaseModel


class MemberItem(BaseModel):
    userId: str
    name: str
    role: str


class MemberListData(BaseModel):
    list: List[MemberItem]


class UpdateMemberRoleRequest(BaseModel):
    role: str


class OkData(BaseModel):
    ok: bool


class AddMemberRequest(BaseModel):
    userId: str
    role: str = "member"
