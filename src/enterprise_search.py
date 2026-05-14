"""
企业检索统一入口：关键词 / 向量 / 混合（RRF）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.config import (
    HYBRID_VECTOR_POOL,
    LAYER1_CANDIDATE_CAP,
    RETRIEVAL_MODE,
    RRF_K,
)
from src.enterprise_vector_index import EnterpriseVectorIndex
from src.vector_store import KeywordSearch, build_keyword_searcher


def _enterprise_id(item: Dict[str, Any]) -> str:
    md = item.get("metadata") or {}
    eid = md.get("enterprise_id")
    if eid is not None and str(eid).strip() != "":
        return str(eid)
    name = md.get("企业名称") or ""
    return "__name__:" + str(name)


def _merge_kw_vec_items(
    kw_item: Optional[Dict[str, Any]],
    vec_item: Optional[Dict[str, Any]],
    rrf_s: float,
    max_rrf: float,
) -> Dict[str, Any]:
    max_rrf = max_rrf or 1e-9
    score = round(100.0 * rrf_s / max_rrf, 2)
    if kw_item and vec_item:
        out = {
            "content": kw_item.get("content") or vec_item.get("content", ""),
            "metadata": dict(kw_item.get("metadata") or {}),
            "score": score,
            "matched_keywords": list(kw_item.get("matched_keywords") or []),
            "rrf_score": rrf_s,
        }
        mk = out["matched_keywords"]
        if "[向量]" not in mk:
            out["matched_keywords"] = mk + ["[向量]"]
        return out
    if kw_item:
        o = dict(kw_item)
        o["score"] = score
        o["rrf_score"] = rrf_s
        return o
    if vec_item:
        o = dict(vec_item)
        o["score"] = score
        o["rrf_score"] = rrf_s
        return o
    return {"content": "", "metadata": {}, "score": score, "matched_keywords": [], "rrf_score": rrf_s}


def reciprocal_rank_fusion_merge(
    keyword_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    top_k: int,
    rrf_k: int = None,
) -> List[Dict[str, Any]]:
    rrf_k = rrf_k if rrf_k is not None else RRF_K
    kw_by_id = {_enterprise_id(x): x for x in keyword_results}
    vec_by_id = {_enterprise_id(x): x for x in vector_results}
    rrf_scores: Dict[str, float] = {}
    for rank, item in enumerate(keyword_results):
        eid = _enterprise_id(item)
        rrf_scores[eid] = rrf_scores.get(eid, 0.0) + 1.0 / (rrf_k + rank + 1)
    for rank, item in enumerate(vector_results):
        eid = _enterprise_id(item)
        rrf_scores[eid] = rrf_scores.get(eid, 0.0) + 1.0 / (rrf_k + rank + 1)
    ordered = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
    if not ordered:
        return []
    max_rrf = rrf_scores[ordered[0]]
    merged: List[Dict[str, Any]] = []
    for eid in ordered[:top_k]:
        merged.append(
            _merge_kw_vec_items(
                kw_by_id.get(eid),
                vec_by_id.get(eid),
                rrf_scores[eid],
                max_rrf,
            )
        )
    return merged


class VectorEnterpriseSearcher:
    def __init__(self, excel_path: Optional[str] = None, persist_dir: Optional[str] = None):
        self._index = EnterpriseVectorIndex(excel_path=excel_path, persist_dir=persist_dir)

    def search_with_expansion(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        return self._index.search_with_expansion(query, top_k=top_k)

    def get_info(self) -> Dict[str, Any]:
        return self._index.get_info()


class HybridLegacyEnterpriseSearcher:
    """混合检索（旧版）：全库向量 + 关键词并行，RRF 融合。"""

    def __init__(self, excel_path: Optional[str] = None, persist_dir: Optional[str] = None):
        self._keyword: KeywordSearch = build_keyword_searcher(excel_path=excel_path)
        self._vector = EnterpriseVectorIndex(excel_path=excel_path, persist_dir=persist_dir)

    def search_with_expansion(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        pool = max(HYBRID_VECTOR_POOL, top_k * 2)
        kw = self._keyword.search_with_expansion(query, top_k=min(pool, 80))
        self._vector.ensure_index()
        vec = self._vector.search(query, top_k=min(pool, max(20, self._vector.collection_count())))
        return reciprocal_rank_fusion_merge(kw, vec, top_k=top_k, rrf_k=RRF_K)

    def get_info(self) -> Dict[str, Any]:
        vi = self._vector.get_info()
        ki = self._keyword.get_info()
        return {
            "企业数量": ki.get("企业数量"),
            "检索方式": "hybrid_legacy",
            "数据来源": ki.get("数据来源"),
            "向量目录": vi.get("向量目录"),
            "嵌入模型": vi.get("嵌入模型"),
        }


class HybridEnterpriseSearcher:
    def __init__(self, excel_path: Optional[str] = None, persist_dir: Optional[str] = None):
        self._keyword: KeywordSearch = build_keyword_searcher(excel_path=excel_path)
        self._vector = EnterpriseVectorIndex(excel_path=excel_path, persist_dir=persist_dir)

    def search_with_expansion(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        cap = max(LAYER1_CANDIDATE_CAP, top_k, HYBRID_VECTOR_POOL)
        layer1 = self._keyword.search_layer1_ranked(query, cap=cap)
        candidate_ids = [_enterprise_id(x) for x in layer1]
        self._vector.ensure_index()
        pool = max(HYBRID_VECTOR_POOL, top_k * 2)
        vec_top = min(pool, max(20, len(candidate_ids)), max(1, self._vector.collection_count()))
        layer2 = self._vector.search_subset(query, candidate_ids, top_k=vec_top)
        if not layer2 and self._vector.collection_count() > 0:
            layer2 = self._vector.search(query, top_k=min(vec_top, self._vector.collection_count()))
        return reciprocal_rank_fusion_merge(layer1, layer2, top_k=top_k, rrf_k=RRF_K)

    def get_info(self) -> Dict[str, Any]:
        vi = self._vector.get_info()
        ki = self._keyword.get_info()
        return {
            "企业数量": ki.get("企业数量"),
            "检索方式": "hybrid",
            "子策略": "layer1_field_keyword_funnel + layer2_vector_subset_rrf",
            "数据来源": ki.get("数据来源"),
            "向量目录": vi.get("向量目录"),
            "嵌入模型": vi.get("嵌入模型"),
        }


def build_enterprise_searcher(
    mode: Optional[str] = None,
    excel_path: Optional[str] = None,
    persist_dir: Optional[str] = None,
):
    """
    构建企业检索器（与 KeywordSearch 相同方法：search_with_expansion、get_info）。

    mode: keyword | vector | hybrid | hybrid_legacy，默认读取 config.RETRIEVAL_MODE。
    """
    m = (mode or RETRIEVAL_MODE or "hybrid").strip().lower()
    if m not in ("keyword", "vector", "hybrid", "hybrid_legacy"):
        m = "hybrid"

    if m == "keyword":
        return build_keyword_searcher(excel_path=excel_path)

    try:
        if m == "vector":
            return VectorEnterpriseSearcher(excel_path=excel_path, persist_dir=persist_dir)
        if m == "hybrid_legacy":
            return HybridLegacyEnterpriseSearcher(excel_path=excel_path, persist_dir=persist_dir)
        return HybridEnterpriseSearcher(excel_path=excel_path, persist_dir=persist_dir)
    except Exception as e:
        print(f"⚠️ 向量检索初始化失败（{e}），回退为关键词检索。")
        return build_keyword_searcher(excel_path=excel_path)
