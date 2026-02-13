from typing import Dict

from pydantic import BaseModel


class LoginRequest(BaseModel):
    provider: str
    code: str
    inviteCode: str | None = None


class UserInfo(BaseModel):
    id: str
    name: str
    avatar: str | None = None


class LoginData(BaseModel):
    token: str
    user: UserInfo


class UpdateUserProfileRequest(BaseModel):
    name: str | None = None
    avatarFileId: str | None = None


class AvatarUploadTokenRequest(BaseModel):
    name: str
    size: int
    type: str


class AvatarUploadTokenData(BaseModel):
    fileId: str
    uploadUrl: str
    method: str
    headers: Dict[str, str]
    finalUrl: str
