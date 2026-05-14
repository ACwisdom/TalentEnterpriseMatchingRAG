from __future__ import annotations

import os
from typing import Any, Mapping

import httpx
from pydantic import TypeAdapter

from langgraph_tools.errors import ApiError, map_error_response
from langgraph_tools.headers import auth_headers, correlation_headers, idempotency_headers
from langgraph_tools.models import (
    CommunicationDto,
    CreateCommunicationRequest,
    CreateRecommendationRequest,
    CreateReminderRequest,
    OutboundMessageRequest,
    OutboundQueuedResponse,
    PagedResponse,
    PatchRecommendationStatusRequest,
    RecommendationDto,
    ReminderDto,
    CandidateDto,
    JobDto,
)


_ta_candidates = TypeAdapter(PagedResponse[CandidateDto])
_ta_jobs = TypeAdapter(PagedResponse[JobDto])
def _merge_headers(
    base: Mapping[str, str] | None,
    *,
    correlation_id: str | None,
    idempotency_key: str | None,
    api_key: str | None,
    bearer_token: str | None,
) -> dict[str, str]:
    out: dict[str, str] = dict(base or {})
    out.update(correlation_headers(correlation_id))
    out.update(idempotency_headers(idempotency_key))
    out.update(auth_headers(api_key=api_key, bearer_token=bearer_token))
    return out


class RecruitmentApiClient:
    """Async httpx client for `recruitment-api` v1."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._base = (base_url or os.environ.get("JAVA_API_BASE_URL") or "http://127.0.0.1:8080").rstrip("/")
        self._api_key = api_key or os.environ.get("SERVICE_API_KEY")
        self._bearer = bearer_token
        self._timeout = timeout_s

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        url = f"{self._base}{path}"
        hdrs = _merge_headers(
            headers,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            api_key=self._api_key,
            bearer_token=self._bearer,
        )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.request(method, url, json=json, params=params, headers=hdrs)
        if resp.status_code >= 400:
            try:
                data = resp.json()
            except Exception as exc:  # noqa: BLE001
                raise ApiError("HTTP_ERROR", resp.text or str(resp.status_code)) from exc
            if isinstance(data, dict) and "code" in data:
                raise map_error_response(data)
            raise ApiError("HTTP_ERROR", resp.text or str(resp.status_code))
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def search_candidates(
        self,
        *,
        name: str | None = None,
        email: str | None = None,
        skill: str | None = None,
        page: int = 0,
        size: int = 20,
        correlation_id: str | None = None,
    ) -> PagedResponse[CandidateDto]:
        data = await self._request(
            "GET",
            "/api/v1/candidates/search",
            params={"name": name, "email": email, "skill": skill, "page": page, "size": size},
            correlation_id=correlation_id,
        )
        return _ta_candidates.validate_python(data)

    async def search_jobs(
        self,
        *,
        company_id: int | None = None,
        title: str | None = None,
        status: str | None = None,
        page: int = 0,
        size: int = 20,
        correlation_id: str | None = None,
    ) -> PagedResponse[JobDto]:
        data = await self._request(
            "GET",
            "/api/v1/jobs/search",
            params={
                "companyId": company_id,
                "title": title,
                "status": status,
                "page": page,
                "size": size,
            },
            correlation_id=correlation_id,
        )
        return _ta_jobs.validate_python(data)

    async def create_recommendation(
        self,
        body: CreateRecommendationRequest,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> RecommendationDto:
        data = await self._request(
            "POST",
            "/api/v1/recommendations",
            json=body.model_dump(exclude_none=True),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        return RecommendationDto.model_validate(data)

    async def patch_recommendation_status(
        self,
        recommendation_id: int,
        body: PatchRecommendationStatusRequest,
        *,
        correlation_id: str | None = None,
    ) -> RecommendationDto:
        data = await self._request(
            "PATCH",
            f"/api/v1/recommendations/{recommendation_id}/status",
            json=body.model_dump(exclude_none=True),
            correlation_id=correlation_id,
        )
        return RecommendationDto.model_validate(data)

    async def add_communication(
        self,
        recommendation_id: int,
        body: CreateCommunicationRequest,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> CommunicationDto:
        data = await self._request(
            "POST",
            f"/api/v1/recommendations/{recommendation_id}/communications",
            json=body.model_dump(),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        return CommunicationDto.model_validate(data)

    async def queue_outbound_message(
        self,
        body: OutboundMessageRequest,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> OutboundQueuedResponse:
        data = await self._request(
            "POST",
            "/api/v1/messages/outbound",
            json=body.model_dump(exclude_none=True),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        return OutboundQueuedResponse.model_validate(data)

    async def create_reminder(
        self,
        body: CreateReminderRequest,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ReminderDto:
        payload = body.model_dump(mode="json", exclude_none=True)
        data = await self._request(
            "POST",
            "/api/v1/reminders",
            json=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        return ReminderDto.model_validate(data)
