"""
LTR 轻量特征：列名与特征向量顺序需与训练脚本、示例 CSV 一致。
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

# sklearn 训练/推理时按此顺序拼接特征矩阵列
LTR_FEAT_RECALL_NORM = "recall_norm"
LTR_FEAT_CE_NORM = "ce_norm"
LTR_FEAT_RULE_BONUS = "rule_bonus"
LTR_FEAT_PROVINCE_HIT = "province_hit"
LTR_FEAT_CITY_HIT = "city_hit"
LTR_FEAT_FIELD_HIT = "field_hit"
LTR_FEAT_KW_COUNT = "kw_count"

FEATURE_COLUMNS: List[str] = [
    LTR_FEAT_RECALL_NORM,
    LTR_FEAT_CE_NORM,
    LTR_FEAT_RULE_BONUS,
    LTR_FEAT_PROVINCE_HIT,
    LTR_FEAT_CITY_HIT,
    LTR_FEAT_FIELD_HIT,
    LTR_FEAT_KW_COUNT,
]


def feature_row_from_ranking_parts(
    recall_norm: float,
    ce_norm: float,
    rule_bonus: float,
    province_hit: float,
    city_hit: float,
    field_hit: float,
    kw_count: float,
) -> List[float]:
    return [
        float(recall_norm),
        float(ce_norm),
        float(rule_bonus),
        float(province_hit),
        float(city_hit),
        float(field_hit),
        float(kw_count),
]


def feature_dict_to_row(d: Dict[str, Any]) -> List[float]:
    return [float(d.get(name, 0.0) or 0.0) for name in FEATURE_COLUMNS]


def row_to_feature_dict(row: Sequence[float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for i, name in enumerate(FEATURE_COLUMNS):
        out[name] = float(row[i]) if i < len(row) else 0.0
    return out
