import httpx
import pytest

from langgraph_tools.client import RecruitmentJavaClient
from langgraph_tools.errors import ConflictError, RecruitmentApiError, ValidationError


def test_raise_conflict_on_409():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"code": "DUPLICATE_RECOMMENDATION", "message": "dup", "details": {"existingId": 1}},
        )

    transport = httpx.MockTransport(handler)

    async def run():
        c = RecruitmentJavaClient(base_url="http://test", api_key="k", transport=transport)
        try:
            with pytest.raises(ConflictError):
                await c.create_recommendation({"jobId": 1, "candidateId": 2})
        finally:
            await c.aclose()

    import asyncio

    asyncio.run(run())


def test_raise_validation_on_422():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"code": "INVALID_STATUS_TRANSITION", "message": "bad", "details": {}},
        )

    transport = httpx.MockTransport(handler)

    async def run():
        c = RecruitmentJavaClient(base_url="http://test", api_key="k", transport=transport)
        try:
            with pytest.raises(ValidationError):
                await c.patch_recommendation_status(9, {"status": "入职"})
        finally:
            await c.aclose()

    import asyncio

    asyncio.run(run())


def test_search_candidates_ok():
    body = {"items": [], "page": {"number": 0, "size": 20, "totalElements": 0, "totalPages": 0}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-api-key") == "k"
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)

    async def run():
        c = RecruitmentJavaClient(base_url="http://test", api_key="k", transport=transport)
        try:
            out = await c.search_candidates()
            assert out["page"]["totalElements"] == 0
        finally:
            await c.aclose()

    import asyncio

    asyncio.run(run())
