"""地域/领域硬过滤、排除 ID、最低召回分（不加载 CrossEncoder）。"""
from __future__ import annotations

import pytest

from src.match_constraints import MatchConstraints
from src.match_rerank import rerank_enterprises


def _ent(
    eid: str,
    province: str,
    city: str,
    score: float,
    prod: str = "产品",
) -> dict:
    return {
        "score": score,
        "metadata": {
            "enterprise_id": eid,
            "企业名称": f"企业{eid}",
            "省": province,
            "市": city,
            "区/县": "",
            "地区门槛": "",
            "一级领域": "一级",
            "二级领域": "二级",
            "企业主要产品": prod,
        },
        "matched_keywords": ["kw1"],
    }


@pytest.fixture(autouse=True)
def no_ce(monkeypatch):
    monkeypatch.setenv("RERANK_ENABLED", "0")


def test_hard_region_drops_non_matching():
    c = MatchConstraints(provinces=("江苏",), hard_region=True)
    candidates = [
        _ent("1", "浙江", "杭州", 90.0),
        _ent("2", "江苏", "苏州", 50.0),
    ]
    out, meta = rerank_enterprises("求职江苏", candidates, 10, c)
    assert meta.get("hard_filter_dropped", 0) >= 1
    assert len(out) == 1
    assert out[0]["metadata"]["省"] == "江苏"


def test_hard_field_requires_keyword():
    c = MatchConstraints(field_keywords=("封装",), hard_field=True)
    candidates = [
        _ent("1", "江苏", "苏州", 90.0, prod="晶圆制造"),
        _ent("2", "江苏", "无锡", 60.0, prod="先进封装产线"),
    ]
    out, meta = rerank_enterprises("熟悉封装工艺", candidates, 10, c)
    assert meta.get("hard_filter_dropped", 0) >= 1
    assert len(out) == 1
    assert "封装" in out[0]["metadata"]["企业主要产品"]


def test_exclude_ids():
    c = MatchConstraints(exclude_ids=("1",))
    candidates = [_ent("1", "江苏", "南京", 99.0), _ent("2", "江苏", "苏州", 50.0)]
    out, meta = rerank_enterprises("简历", candidates, 10, c)
    assert meta.get("exclude_filtered") == 1
    assert out[0]["metadata"]["enterprise_id"] == "2"


def test_min_recall_score_filters():
    c = MatchConstraints(min_recall_score=55.0)
    candidates = [_ent("1", "江苏", "南京", 80.0), _ent("2", "江苏", "苏州", 30.0)]
    out, meta = rerank_enterprises("简历", candidates, 10, c)
    assert meta.get("min_recall_filtered", 0) >= 1
    assert len(out) == 1
    assert out[0]["metadata"]["enterprise_id"] == "1"
