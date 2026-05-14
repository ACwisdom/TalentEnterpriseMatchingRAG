"""
宽召回后的 CrossEncoder 重排、规则加权与可解释字段；可选 LTR joblib 融合。
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.config import ENTERPRISE_FIELDS
from src.ltr_features import FEATURE_COLUMNS, feature_row_from_ranking_parts
from src.match_constraints import MatchConstraints

CrossEncoderType = Any

_ce_singleton: Tuple[Optional[CrossEncoderType], Optional[str], Optional[str]] = (None, None, None)
_ltr_singleton: Tuple[Optional[Any], Optional[str]] = (None, None)


def _norm_geo(s: str) -> str:
    t = (s or "").strip().replace(" ", "")
    for suf in ("省", "市", "自治区", "壮族自治区", "回族自治区", "维吾尔自治区"):
        t = t.replace(suf, "")
    return t.lower()


def _geo_hit(query_vals: Sequence[str], cell: str) -> bool:
    if not query_vals:
        return False
    c = _norm_geo(cell)
    if not c:
        return False
    for q in query_vals:
        nq = _norm_geo(str(q))
        if not nq:
            continue
        if nq in c or c in nq or nq == c:
            return True
    return False


def _field_blob(md: Dict[str, Any]) -> str:
    parts = [
        str(md.get("一级领域") or ""),
        str(md.get("二级领域") or ""),
        str(md.get("企业主要产品") or ""),
    ]
    return " ".join(parts)


def _field_keyword_hit(keywords: Sequence[str], md: Dict[str, Any]) -> bool:
    blob = _field_blob(md)
    if not blob.strip():
        return False
    for kw in keywords:
        k = str(kw).strip()
        if k and k in blob:
            return True
    return False


def _enterprise_pair_text(ent: Dict[str, Any]) -> str:
    md = ent.get("metadata") or {}
    lines: List[str] = []
    for key in ENTERPRISE_FIELDS:
        v = md.get(key)
        if v is not None and str(v).strip():
            lines.append(f"{key}：{str(v).strip()}")
    if not lines and ent.get("content"):
        return str(ent.get("content"))[:2000]
    return "\n".join(lines)


def _get_cross_encoder() -> Tuple[Optional[CrossEncoderType], str, Optional[str]]:
    global _ce_singleton
    from src.config import RERANK_CROSS_ENCODER_MODEL, RERANK_ENABLED

    if not RERANK_ENABLED:
        return None, "disabled", None

    model_name = RERANK_CROSS_ENCODER_MODEL
    err: Optional[str] = _ce_singleton[2]
    if _ce_singleton[0] is not None and _ce_singleton[1] == model_name:
        return _ce_singleton[0], model_name, err

    try:
        from sentence_transformers import CrossEncoder  # type: ignore

        ce = CrossEncoder(model_name, max_length=512)
        _ce_singleton = (ce, model_name, None)
        return ce, model_name, None
    except Exception as e:  # noqa: BLE001
        err = str(e)
        _ce_singleton = (None, model_name, err)
        return None, model_name, err


def _get_ltr_model():
    global _ltr_singleton
    from src.config import LTR_INFERENCE_ENABLED, LTR_MODEL_PATH, RERANK_WEIGHT_LTR

    if float(RERANK_WEIGHT_LTR) <= 0:
        return None, None

    path = (LTR_MODEL_PATH or "").strip()
    if not LTR_INFERENCE_ENABLED or not path or not os.path.isfile(path):
        return None, None

    if _ltr_singleton[1] == path and _ltr_singleton[0] is not None:
        return _ltr_singleton[0], path

    try:
        import joblib

        m = joblib.load(path)
        if isinstance(m, dict) and "model" in m:
            m = m["model"]
        _ltr_singleton = (m, path)
        return m, path
    except Exception:  # noqa: BLE001
        _ltr_singleton = (None, path)
        return None, path


def _minmax_norm(scores: List[float]) -> List[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [0.5 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def _normalize_weights(w_rec: float, w_ce: float, w_rule: float, w_ltr: float, ce_ok: bool, ltr_ok: bool) -> Tuple[float, float, float, float]:
    wr, wc, wu, wl = max(0.0, w_rec), max(0.0, w_ce), max(0.0, w_rule), max(0.0, w_ltr)
    if not ce_ok:
        wc = 0.0
    if not ltr_ok:
        wl = 0.0
    s = wr + wc + wu + wl
    if s <= 0:
        return 1.0, 0.0, 0.0, 0.0
    return wr / s, wc / s, wu / s, wl / s


def _enterprise_id(ent: Dict[str, Any]) -> str:
    md = ent.get("metadata") or {}
    eid = md.get("enterprise_id")
    if eid is not None and str(eid).strip() != "":
        return str(eid).strip()
    name = md.get("企业名称") or ""
    return "__name__:" + str(name)


def _apply_hard_filters(
    enterprises: List[Dict[str, Any]],
    c: MatchConstraints,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """硬过滤：地区/领域；返回 (保留列表, 丢弃原因样例)。"""
    reasons: List[str] = []
    out: List[Dict[str, Any]] = []
    for ent in enterprises:
        md = ent.get("metadata") or {}
        ok = True
        if c.hard_region and (c.provinces or c.cities):
            prov_ok = _geo_hit(c.provinces, str(md.get("省") or "")) if c.provinces else False
            city_ok = _geo_hit(c.cities, str(md.get("市") or "")) if c.cities else False
            if c.provinces and c.cities:
                if not (prov_ok or city_ok):
                    ok = False
                    reasons.append("硬过滤：省/市均未命中约束")
            elif c.provinces and not prov_ok:
                ok = False
                reasons.append("硬过滤：省份未命中")
            elif c.cities and not city_ok:
                ok = False
                reasons.append("硬过滤：城市未命中")
        if ok and c.hard_field and c.field_keywords:
            if not _field_keyword_hit(c.field_keywords, md):
                ok = False
                reasons.append("硬过滤：领域/产品关键词未命中")
        if ok:
            out.append(ent)
    return out, reasons


def _rule_signals(
    md: Dict[str, Any],
    c: MatchConstraints,
) -> Tuple[float, List[str], float, float, float]:
    """
    规则加分 0~1 与命中标记；reasons 为简短中文说明。
    """
    bonus = 0.0
    reasons: List[str] = []
    ph = 1.0 if _geo_hit(c.provinces, str(md.get("省") or "")) else 0.0
    ch = 1.0 if _geo_hit(c.cities, str(md.get("市") or "")) else 0.0
    fh = 1.0 if _field_keyword_hit(c.field_keywords, md) else 0.0

    if c.provinces and ph:
        bonus += 0.25
        reasons.append("省份与意向地区一致")
    if c.cities and ch:
        bonus += 0.25
        reasons.append("城市与意向地区一致")
    if c.field_keywords and fh:
        bonus += 0.35
        reasons.append("领域/产品与关键词匹配")
    bonus = min(1.0, bonus)
    return bonus, reasons, ph, ch, fh


def rerank_enterprises(
    resume_text: str,
    enterprises: List[Dict[str, Any]],
    top_k: int,
    constraints: Optional[MatchConstraints] = None,
    cross_encoder_factory: Optional[Callable[[], Tuple[Optional[Any], str, Optional[str]]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    对宽召回结果重排，写入 ranking / ranking_reasons，score 为最终融合分（0–100）。
    """
    from src.config import (
        RERANK_BATCH_SIZE,
        RERANK_ENABLED,
        RERANK_MIN_RECALL_SCORE,
        RERANK_WEIGHT_CE,
        RERANK_WEIGHT_LTR,
        RERANK_WEIGHT_RECALL,
        RERANK_WEIGHT_RULE,
    )

    c = constraints or MatchConstraints.empty()
    meta: Dict[str, Any] = {
        "rerank_enabled": bool(RERANK_ENABLED),
        "constraints": c.to_summary(),
    }

    if not enterprises:
        return [], meta

    pool = list(enterprises)
    if c.exclude_ids:
        excl = {str(x).strip() for x in c.exclude_ids if str(x).strip()}
        before_ex = len(pool)
        pool = [e for e in pool if _enterprise_id(e) not in excl]
        meta["exclude_filtered"] = before_ex - len(pool)
    hard_drop_notes: List[str] = []
    if c.hard_region or c.hard_field:
        before_hard = len(pool)
        pool, hard_drop_notes = _apply_hard_filters(pool, c)
        meta["hard_filter_dropped"] = before_hard - len(pool)
        if hard_drop_notes:
            meta["hard_filter_sample_reasons"] = hard_drop_notes[:5]

    min_rs = c.min_recall_score
    if min_rs is None:
        min_rs = float(RERANK_MIN_RECALL_SCORE)
    if min_rs and min_rs > 0:
        kept = [e for e in pool if float(e.get("score") or 0.0) >= min_rs]
        meta["min_recall_filtered"] = len(pool) - len(kept)
        pool = kept

    if not pool:
        meta["warning"] = "硬过滤或最低召回分后无候选"
        return [], meta

    # 保留原始召回分
    originals = [float(e.get("score") or 0.0) for e in pool]
    recall_norms = [min(1.0, max(0.0, s / 100.0)) for s in originals]

    factory = cross_encoder_factory or _get_cross_encoder
    ce_model, ce_name, ce_err = factory()
    ce_ok = ce_model is not None and (cross_encoder_factory is not None or bool(RERANK_ENABLED))
    meta["cross_encoder_model"] = ce_name
    if ce_err:
        meta["cross_encoder_error"] = ce_err

    ce_raw: List[float] = [0.0] * len(pool)
    if ce_ok:
        from src.config import RERANK_ENTERPRISE_MAX_CHARS, RERANK_RESUME_MAX_CHARS

        rtxt = (resume_text or "")[: int(RERANK_RESUME_MAX_CHARS)]
        pairs = [
            [rtxt, _enterprise_pair_text(e)[: int(RERANK_ENTERPRISE_MAX_CHARS)]]
            for e in pool
        ]
        try:
            raw = ce_model.predict(pairs, batch_size=max(1, int(RERANK_BATCH_SIZE)))
            ce_raw = [float(x) for x in np.asarray(raw).reshape(-1).tolist()]
        except Exception as e:  # noqa: BLE001
            meta["cross_encoder_predict_error"] = str(e)
            ce_ok = False
            ce_raw = [0.0] * len(pool)

    ce_norms = _minmax_norm(ce_raw) if ce_ok else [0.0] * len(pool)

    ltr_m, ltr_path = _get_ltr_model()
    ltr_ok = ltr_m is not None
    meta["ltr_model_path"] = ltr_path
    meta["ltr_active"] = ltr_ok

    wr, wc, wu, wl = _normalize_weights(
        float(RERANK_WEIGHT_RECALL),
        float(RERANK_WEIGHT_CE),
        float(RERANK_WEIGHT_RULE),
        float(RERANK_WEIGHT_LTR),
        ce_ok,
        ltr_ok,
    )
    meta["blend_weights"] = {"recall": wr, "cross_encoder": wc, "rule": wu, "ltr": wl}

    scored: List[Dict[str, Any]] = []
    for i, ent in enumerate(pool):
        md = ent.get("metadata") or {}
        rsn = recall_norms[i]
        ce_n = ce_norms[i] if ce_ok else 0.0
        rule_b, rule_reasons, ph, ch, fh = _rule_signals(md, c)

        kw_list = ent.get("matched_keywords") or []
        kw_count = min(20.0, float(len(kw_list)))

        ltr_score_norm = 0.0
        if ltr_ok:
            feat = feature_row_from_ranking_parts(rsn, ce_n, rule_b, ph, ch, fh, kw_count)
            X = np.asarray([feat], dtype=np.float32)
            try:
                if hasattr(ltr_m, "predict_proba"):
                    pr = ltr_m.predict_proba(X)[0]
                    ltr_score_norm = float(pr[1]) if len(pr) > 1 else float(pr[0])
                else:
                    v = float(np.asarray(ltr_m.decision_function(X)).reshape(-1)[0])
                    ltr_score_norm = 1.0 / (1.0 + np.exp(-v))
            except Exception:  # noqa: BLE001
                ltr_score_norm = 0.0

        final_01 = wr * rsn + wc * ce_n + wu * rule_b + wl * ltr_score_norm
        final_score = round(float(final_01) * 100.0, 4)

        reasons: List[str] = []
        if ce_ok:
            reasons.append(f"CrossEncoder 相对分 {ce_n:.2f}（模型 {ce_name}）")
        reasons.extend(rule_reasons)
        if not reasons:
            reasons.append("以召回分为主排序")
        if (c.salary_expectation_note or "").strip():
            reasons.append(
                "薪资期望（用户填写）："
                + c.salary_expectation_note.strip()
                + "（企业库无薪资字段，未做硬性比对）"
            )

        ranking = {
            "recall_score": originals[i],
            "recall_norm": round(rsn, 6),
            "ce_norm": round(ce_n, 6),
            "ce_raw": round(ce_raw[i], 6) if ce_ok else None,
            "rule_bonus": round(rule_b, 6),
            "ltr_norm": round(ltr_score_norm, 6) if ltr_ok else None,
            "final": final_score,
            "weights": {"recall": wr, "cross_encoder": wc, "rule": wu, "ltr": wl},
        }

        new_e = dict(ent)
        new_e["score"] = final_score
        new_e["recall_score"] = originals[i]
        new_e["ranking"] = ranking
        new_e["ranking_reasons"] = reasons[:8]
        new_e["ltr_features"] = dict(zip(FEATURE_COLUMNS, feature_row_from_ranking_parts(rsn, ce_n, rule_b, ph, ch, fh, kw_count)))
        scored.append(new_e)

    scored.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    meta["rerank_applied"] = True
    meta["output_size"] = min(top_k, len(scored))
    return scored[:top_k], meta


def compute_wide_recall_top_n(top_k: int) -> int:
    """宽召回池大小：min(cap, max(top_k * multiplier, top_k))。"""
    from src.config import RECALL_TOP_CAP, RECALL_TOP_MULTIPLIER

    tk = max(1, int(top_k))
    mult = max(int(round(tk * float(RECALL_TOP_MULTIPLIER))), tk)
    return min(int(RECALL_TOP_CAP), mult)


def wide_recall_top_n(top_k: int) -> int:
    """兼容旧名，等价于 compute_wide_recall_top_n。"""
    return compute_wide_recall_top_n(top_k)


def rerank_after_recall(
    resume_text: str,
    candidates: List[Dict[str, Any]],
    constraints: MatchConstraints,
    top_k: int,
    cross_encoder_factory: Optional[Callable[[], Tuple[Optional[Any], str, Optional[str]]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """兼容旧名，等价于 rerank_enterprises。"""
    return rerank_enterprises(
        resume_text, candidates, top_k, constraints, cross_encoder_factory=cross_encoder_factory
    )


def match_score_thresholds() -> Tuple[float, float]:
    from src.config import MATCH_SCORE_HIGH, MATCH_SCORE_MID

    return float(MATCH_SCORE_HIGH), float(MATCH_SCORE_MID)
