from __future__ import annotations

import uuid
from typing import Mapping


def correlation_headers(existing: str | None = None) -> dict[str, str]:
    cid = existing or str(uuid.uuid4())
    return {"X-Correlation-Id": cid}


def idempotency_headers(key: str | None) -> dict[str, str]:
    if not key:
        return {}
    return {"Idempotency-Key": key}


def auth_headers(*, api_key: str | None = None, bearer_token: str | None = None) -> dict[str, str]:
    if api_key:
        return {"X-API-Key": api_key}
    if bearer_token:
        return {"Authorization": f"Bearer {bearer_token}"}
    return {}
