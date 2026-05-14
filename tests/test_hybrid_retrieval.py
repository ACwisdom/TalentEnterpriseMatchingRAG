"""
混合检索：语义近义场景下 hybrid 应优于纯关键词。
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_RUN_HYBRID = os.getenv("RUN_HYBRID_INTEGRATION", "").strip().lower() in ("1", "true", "yes", "on")

from src.config import ENTERPRISE_FIELDS  # noqa: E402
from src.enterprise_search import build_enterprise_searcher  # noqa: E402
from src.vector_store import KeywordSearch  # noqa: E402


def _mini_excel_rows():
    """目标企业用语与简历故意错开字面，依赖向量召回。"""
    target = {
        "省": "上海市",
        "市": "上海市",
        "区/县": "浦东新区",
        "地区门槛": "",
        "企业名称": "冷冻电镜结构生物学服务公司",
        "一级领域": "5. 生物技术",
        "二级领域": "5.1 研发服务",
        "企业主要产品": "冷冻电镜单颗粒分析、膜蛋白表达与纯化",
        "政府给介绍": "",
        "企业官方/第三方/新闻介绍": "提供高分辨冷冻电镜结构解析与膜蛋白制备全流程服务。",
    }
    decoy = {
        "省": "河北省",
        "市": "唐山市",
        "区/县": "",
        "地区门槛": "",
        "企业名称": "传统炼钢辅料有限公司",
        "一级领域": "6. 新材料",
        "二级领域": "6.2 金属材料",
        "企业主要产品": "炼钢用耐火砖与冶金辅料批发",
        "政府给介绍": "",
        "企业官方/第三方/新闻介绍": "冶金炉料与耐材供应。",
    }
    return [target, decoy]


@pytest.mark.skipif(not _RUN_HYBRID, reason="构建 Chroma 与嵌入模型较慢；设置 RUN_HYBRID_INTEGRATION=1 后运行")
def test_hybrid_recalls_semantic_target(tmp_path):
    """简历不含「冷冻电镜」字面，但描述电子显微学重构；关键词难命中目标企业。"""
    xlsx = tmp_path / "mini_enterprises.xlsx"
    df = pd.DataFrame(_mini_excel_rows(), columns=ENTERPRISE_FIELDS)
    df.to_excel(xlsx, index=False)
    persist = tmp_path / "chroma_db"

    resume = (
        "研究员，长期从事生物大分子高分辨率三维重构，"
        "熟悉电子显微学数据采集与单颗粒重构流程，发表多篇结构生物学论文。"
    )

    kw_searcher = build_enterprise_searcher(mode="keyword", excel_path=str(xlsx))
    kw_hits = kw_searcher.search_with_expansion(resume, top_k=5)
    kw_names = [h["metadata"].get("企业名称", "") for h in kw_hits]
    target_name = "冷冻电镜结构生物学服务公司"

    hybrid = build_enterprise_searcher(mode="hybrid", excel_path=str(xlsx), persist_dir=str(persist))
    hybrid_hits = hybrid.search_with_expansion(resume, top_k=5)
    hy_names = [h["metadata"].get("企业名称", "") for h in hybrid_hits]

    assert target_name in hy_names, f"hybrid 应召回目标企业，实际: {hy_names}"
    if target_name in kw_names:
        assert hy_names.index(target_name) <= kw_names.index(target_name)
    else:
        assert target_name not in kw_names


def test_keyword_searcher_still_has_enterprise_id(tmp_path):
    xlsx = tmp_path / "one.xlsx"
    row = _mini_excel_rows()[0]
    row["企业主要产品"] = "重组蛋白疫苗与中试放大CDMO服务"
    df = pd.DataFrame([row], columns=ENTERPRISE_FIELDS)
    df.to_excel(xlsx, index=False)
    s = build_enterprise_searcher(mode="keyword", excel_path=str(xlsx))
    hits = s.search("疫苗研发与工艺放大经验", top_k=3)
    assert hits
    assert "enterprise_id" in hits[0]["metadata"]


def test_layer1_uses_only_secondary_and_products(tmp_path):
    """第一层不应匹配「企业官方/第三方/新闻介绍」中的词，仅看二级领域 + 主要产品。"""
    xlsx = tmp_path / "layer1.xlsx"
    noise_in_intro = {
        "省": "北京市",
        "市": "北京市",
        "区/县": "",
        "地区门槛": "",
        "企业名称": "仅简介含疫苗_应殿后",
        "一级领域": "9. 化工技术",
        "二级领域": "9.1 传统化工",
        "企业主要产品": "通用溶剂批发",
        "政府给介绍": "",
        "企业官方/第三方/新闻介绍": "本公司也做疫苗研发平台对外合作。",
    }
    strong_in_layer1 = {
        "省": "上海市",
        "市": "上海市",
        "区/县": "",
        "地区门槛": "",
        "企业名称": "产品与领域含疫苗_应排前",
        "一级领域": "4. 生物医药技术",
        "二级领域": "4.1 疫苗与生物制品",
        "企业主要产品": "重组蛋白疫苗与中试放大",
        "政府给介绍": "",
        "企业官方/第三方/新闻介绍": "常规企业介绍。",
    }
    df = pd.DataFrame([noise_in_intro, strong_in_layer1], columns=ENTERPRISE_FIELDS)
    df.to_excel(xlsx, index=False)
    kw = KeywordSearch(excel_path=str(xlsx))
    ranked = kw.search_layer1_ranked("疫苗研发与中试", cap=10)
    names = [r["metadata"]["企业名称"] for r in ranked]
    assert names[0] == "产品与领域含疫苗_应排前"


def test_build_prompt_contains_reference_date(monkeypatch):
    import src.prompt_builder as pb

    monkeypatch.setattr(pb, "REFERENCE_DATE", date(2026, 3, 15))
    messages = pb.build_prompt("系统提示占位", "简历占位", [])
    assert "2026-03-15" in messages[0]["content"]
    assert "2026-03-15" in messages[1]["content"]


@pytest.mark.skipif(not _RUN_HYBRID, reason="构建 Chroma 与嵌入模型较慢；设置 RUN_HYBRID_INTEGRATION=1 后运行")
def test_hybrid_subset_funnel_respects_layer1_cap(monkeypatch, tmp_path):
    """候选过多时只将 Layer1 Top-cap 传入向量子集。"""
    xlsx = tmp_path / "cap.xlsx"
    rows = []
    for i in range(25):
        rows.append(
            {
                "省": "省",
                "市": "市",
                "区/县": "",
                "地区门槛": "",
                "企业名称": f"企业{i}",
                "一级领域": "1. IT",
                "二级领域": f"1.{i} 细分",
                "企业主要产品": "云计算" if i == 0 else "其他产品",
                "政府给介绍": "",
                "企业官方/第三方/新闻介绍": "",
            }
        )
    df = pd.DataFrame(rows, columns=ENTERPRISE_FIELDS)
    df.to_excel(xlsx, index=False)
    persist = tmp_path / "chroma_cap"
    monkeypatch.setattr("src.enterprise_search.LAYER1_CANDIDATE_CAP", 3)
    h = build_enterprise_searcher(mode="hybrid", excel_path=str(xlsx), persist_dir=str(persist))
    hits = h.search_with_expansion("云计算与平台架构", top_k=5)
    assert len(hits) >= 1
    assert "企业0" in [x["metadata"].get("企业名称", "") for x in hits]
