from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException

from app.core.config import settings


@dataclass
class ProviderIdentity:
    provider: str
    openid: str
    unionid: str | None = None


def _resolve_wechat_mini_identity(code: str) -> ProviderIdentity:
    app_id = settings.wechat_mini_app_id.strip()
    app_secret = settings.wechat_mini_app_secret.strip()
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="Wechat mini app credentials are not configured")

    query = urlencode(
        {
            "appid": app_id,
            "secret": app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    base_url = settings.wechat_api_base.rstrip("/")
    endpoint = f"{base_url}/sns/jscode2session?{query}"

    try:
        with urlopen(endpoint, timeout=settings.provider_http_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail="Failed to fetch identity from wechat") from exc

    errcode = payload.get("errcode")
    if errcode:
        if int(errcode) in {40029, 40163}:
            raise HTTPException(status_code=400, detail="Invalid wx.login code")
        errmsg = payload.get("errmsg") or "unknown error"
        raise HTTPException(status_code=502, detail=f"Wechat auth failed: {errmsg}")

    openid = payload.get("openid")
    if not openid:
        raise HTTPException(status_code=502, detail="Wechat auth failed: missing openid")

    unionid = payload.get("unionid")
    return ProviderIdentity(provider="wechat_mini", openid=openid, unionid=unionid)


def resolve_provider_identity(provider: str, code: str) -> ProviderIdentity:
    normalized_provider = provider.strip()
    normalized_code = code.strip()

    if not normalized_provider:
        raise HTTPException(status_code=400, detail="provider is required")
    if not normalized_code:
        raise HTTPException(status_code=400, detail="code is required")

    if normalized_provider == "wechat_mini":
        return _resolve_wechat_mini_identity(normalized_code)

    return ProviderIdentity(provider=normalized_provider, openid=normalized_code)
