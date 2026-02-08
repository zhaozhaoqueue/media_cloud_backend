from pydantic import BaseModel


class LoginRequest(BaseModel):
    code: str
    nickname: str | None = None
    avatar: str | None = None


class UserInfo(BaseModel):
    id: str
    name: str
    avatar: str | None = None


class LoginData(BaseModel):
    token: str
    user: UserInfo
