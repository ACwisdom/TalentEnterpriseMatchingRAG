"""
Optional LangChain ``@tool`` wrappers around :class:`RecruitmentJavaClient`.

Requires ``langchain-core`` (already pulled by this repo's ``langchain`` dependency).
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.tools import tool

from langgraph_tools.client import RecruitmentJavaClient


def _client() -> RecruitmentJavaClient:
    return RecruitmentJavaClient(
        base_url=os.environ.get("JAVA_API_BASE_URL"),
        api_key=os.environ.get("JAVA_SERVICE_API_KEY"),
    )


@tool("java_create_recommendation")
async def java_create_recommendation(job_id: int, candidate_id: int, reason: str = "") -> dict[str, Any]:
    """Create a Recommendation row in Java (facts)."""
    c = _client()
    try:
        return await c.create_recommendation(
            {"jobId": job_id, "candidateId": candidate_id, "reason": reason or None},
        )
    finally:
        await c.aclose()


@tool("java_patch_recommendation_status")
async def java_patch_recommendation_status(recommendation_id: int, status: str, note: str = "") -> dict[str, Any]:
    """PATCH recommendation workflow status (Chinese labels as returned by API)."""
    c = _client()
    try:
        body: dict[str, Any] = {"status": status}
        if note:
            body["note"] = note
        return await c.patch_recommendation_status(recommendation_id, body)
    finally:
        await c.aclose()
