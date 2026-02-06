from pydantic import BaseModel


class LoginRequest(BaseModel):
    code: str


class UserInfo(BaseModel):
    id: str
    name: str
    avatar: str | None = None


class LoginData(BaseModel):
    token: str
    user: UserInfo
