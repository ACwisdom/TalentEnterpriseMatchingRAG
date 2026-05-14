from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

from langgraph_tools.errors import raise_for_status


def _json_or_empty(r: httpx.Response) -> dict[str, Any] | None:
    if not r.content:
        return None
    try:
        out = r.json()
        return out if isinstance(out, dict) else None
    except ValueError:
        return None


class RecruitmentJavaClient:
    """
    Typed async HTTP client for ``/api/v1`` on the Java recruitment service.

    Environment:

    - ``JAVA_API_BASE_URL`` (default ``http://127.0.0.1:8080``)
    - ``JAVA_SERVICE_API_KEY`` (default ``dev-key``, must match Java ``SERVICE_API_KEY``)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = (base_url or os.environ.get("JAVA_API_BASE_URL", "http://127.0.0.1:8080")).rstrip("/")
        self._api_key = api_key or os.environ.get("JAVA_SERVICE_API_KEY", "dev-key")
        self._client = httpx.AsyncClient(
            base_url=self._base,
            timeout=timeout,
            transport=transport,
        )

    def _headers(
        self,
        *,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, str]:
        h: dict[str, str] = {"X-API-Key": self._api_key}
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        if request_id:
            h["X-Request-Id"] = request_id
        else:
            h["X-Request-Id"] = str(uuid.uuid4())
        return h

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search_candidates(
        self,
        *,
        skill: list[str] | None = None,
        city: str | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        exp_years_min: int | None = None,
        q: str | None = None,
        page: int = 0,
        size: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "size": size}
        if skill:
            params["skill"] = skill
        if city is not None:
            params["city"] = city
        if salary_min is not None:
            params["salaryMin"] = salary_min
        if salary_max is not None:
            params["salaryMax"] = salary_max
        if exp_years_min is not None:
            params["expYearsMin"] = exp_years_min
        if q is not None:
            params["q"] = q
        r = await self._client.get("/api/v1/candidates/search", params=params, headers=self._headers())
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}

    async def search_jobs(
        self,
        *,
        candidate_id: int | None = None,
        title_keyword: str | None = None,
        city: str | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        q: str | None = None,
        page: int = 0,
        size: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "size": size}
        if candidate_id is not None:
            params["candidateId"] = candidate_id
        if title_keyword is not None:
            params["titleKeyword"] = title_keyword
        if city is not None:
            params["city"] = city
        if salary_min is not None:
            params["salaryMin"] = salary_min
        if salary_max is not None:
            params["salaryMax"] = salary_max
        if q is not None:
            params["q"] = q
        r = await self._client.get("/api/v1/jobs/search", params=params, headers=self._headers())
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}

    async def create_recommendation(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        r = await self._client.post(
            "/api/v1/recommendations",
            json=body,
            headers=self._headers(idempotency_key=idempotency_key),
        )
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}

    async def patch_recommendation_status(
        self,
        recommendation_id: int,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        r = await self._client.patch(
            f"/api/v1/recommendations/{recommendation_id}/status",
            json=body,
            headers=self._headers(),
        )
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}

    async def create_communication(
        self,
        recommendation_id: int,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        r = await self._client.post(
            f"/api/v1/recommendations/{recommendation_id}/communications",
            json=body,
            headers=self._headers(),
        )
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}

    async def send_outbound_message(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        r = await self._client.post(
            "/api/v1/messages/outbound",
            json=body,
            headers=self._headers(idempotency_key=idempotency_key),
        )
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}

    async def create_reminder(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        r = await self._client.post(
            "/api/v1/reminders",
            json=body,
            headers=self._headers(idempotency_key=idempotency_key),
        )
        payload = _json_or_empty(r)
        raise_for_status(r.status_code, payload)
        return payload or {}
