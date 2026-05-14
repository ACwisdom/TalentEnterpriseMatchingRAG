import os
import secrets
from typing import Optional

from fastapi import HTTPException
from starlette.requests import Request


def _normalize_key(s: str) -> str:
    return s.strip().lstrip("\ufeff")


def _configured_keys() -> list[str]:
    raw_multi = os.getenv("APP_API_KEYS", "").strip()
    raw_single = os.getenv("APP_API_KEY", "").strip()
    keys: list[str] = []
    if raw_multi:
        keys.extend(_normalize_key(k) for k in raw_multi.split(",") if _normalize_key(k))
    nk = _normalize_key(raw_single)
    if nk and nk not in keys:
        keys.append(nk)
    return keys


def _constant_time_match(provided: str, expected: str) -> bool:
    try:
        a = provided.encode("utf-8")
        b = expected.encode("utf-8")
    except UnicodeEncodeError:
        return False
    if len(a) != len(b):
        return False
    return secrets.compare_digest(a, b)


def verify_api_key_value(provided: Optional[str]) -> bool:
    if not provided:
        return False
    provided = _normalize_key(provided)
    if not provided:
        return False
    for k in _configured_keys():
        if _constant_time_match(provided, k):
            return True
    return False


def _extract_client_key(request: Request) -> Optional[str]:
    # ASGI / Starlette：请求头名称统一为小写
    h = request.headers.get("x-api-key")
    if h:
        return h
    auth = request.headers.get("authorization") or ""
    if auth[:7].lower() == "bearer ":
        return auth[7:]
    return None


def _loopback_client(request: Request) -> bool:
    c = request.client
    if not c or not c.host:
        return False
    host = c.host.lower()
    return host in ("127.0.0.1", "localhost", "::1", "::ffff:127.0.0.1")


def browser_must_send_api_key(request: Request) -> bool:
    """从本机浏览器访问时不强制填 X-API-Key；经公网/局域网 IP 访问时仍须带 Key（若已配置）。"""
    return not _loopback_client(request)


async def require_api_key(request: Request) -> None:
    keys = _configured_keys()
    loopback = _loopback_client(request)

    if not keys:
        if loopback:
            return
        raise HTTPException(
            status_code=503,
            detail="Server misconfiguration: set APP_API_KEY or APP_API_KEYS (only optional when using the site from this machine)",
        )

    if loopback:
        return

    if not verify_api_key_value(_extract_client_key(request)):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
