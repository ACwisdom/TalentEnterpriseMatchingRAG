"""CrossEncoder 工厂注入时改变相对排序（不下载真实模型）。"""
from __future__ import annotations

import numpy as np
import pytest

from src.match_constraints import MatchConstraints
from src.match_rerank import rerank_enterprises


def _item(eid: str, recall: float) -> dict:
    return {
        "score": recall,
        "metadata": {
            "enterprise_id": eid,
            "企业名称": eid,
            "省": "江苏",
            "市": "苏州",
            "区/县": "",
            "地区门槛": "",
            "一级领域": "半导体",
            "二级领域": "制造",
            "企业主要产品": "测试产品",
        },
        "matched_keywords": ["半", "导"],
    }


@pytest.fixture(autouse=True)
def weights(monkeypatch):
    monkeypatch.setenv("RERANK_ENABLED", "1")
    monkeypatch.setenv("RERANK_WEIGHT_RECALL", "0.2")
    monkeypatch.setenv("RERANK_WEIGHT_CE", "0.8")
    monkeypatch.setenv("RERANK_WEIGHT_RULE", "0")
    monkeypatch.setenv("RERANK_WEIGHT_LTR", "0")


def test_cross_encoder_factory_changes_order():
    class _MockCE:
        def predict(self, pairs, batch_size=16):
            # 第二条 query-document 对给更高 logit
            return np.array([0.0, 6.0][: len(pairs)], dtype=np.float32)

    def factory():
        return _MockCE(), "mock", None

    c = MatchConstraints.empty()
    candidates = [_item("a", 95.0), _item("b", 60.0)]
    out, meta = rerank_enterprises(
        "半导体设备研发",
        candidates,
        2,
        c,
        cross_encoder_factory=factory,
    )
    assert meta.get("cross_encoder_model") == "mock"
    assert out[0]["metadata"]["enterprise_id"] == "b"
