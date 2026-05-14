"""
Minimal LangGraph workflow that composes a single async step.

Run (with Java API up and SERVICE_API_KEY exported if enabled):

    set PYTHONPATH=.
    python -m langgraph_tools.example_graph
"""

from __future__ import annotations

import asyncio
import os
from typing import TypedDict

from langgraph.graph import END, StateGraph

from langgraph_tools.models import CreateRecommendationRequest
from langgraph_tools.recruitment_client import RecruitmentApiClient


class GraphState(TypedDict, total=False):
    job_id: int
    candidate_id: int
    recommendation_id: int | None


async def create_recommendation_node(state: GraphState) -> GraphState:
    client = RecruitmentApiClient()
    dto = await client.create_recommendation(
        CreateRecommendationRequest(jobId=state["job_id"], candidateId=state["candidate_id"]),
        idempotency_key=os.environ.get("DEMO_IDEMPOTENCY_KEY"),
    )
    return {"recommendation_id": dto.id, **state}


def build_example_graph():
    g = StateGraph(GraphState)
    g.add_node("create_recommendation", create_recommendation_node)
    g.set_entry_point("create_recommendation")
    g.add_edge("create_recommendation", END)
    return g.compile()


async def _demo() -> None:
    job_id = int(os.environ.get("DEMO_JOB_ID", "1"))
    candidate_id = int(os.environ.get("DEMO_CANDIDATE_ID", "1"))
    graph = build_example_graph()
    out = await graph.ainvoke({"job_id": job_id, "candidate_id": candidate_id})
    print(out)


if __name__ == "__main__":
    asyncio.run(_demo())
