"""
匹配阶段可选约束：地区、领域关键词、排除企业 ID、硬过滤与阈值。
用于宽召回后的重排与可解释性；企业库无薪资列，不对企业做薪资硬匹配。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple


def _split_csv(s: Optional[str]) -> Tuple[str, ...]:
    if s is None:
        return ()
    parts = [p.strip() for p in re.split(r"[,，;；\n]+", str(s)) if p.strip()]
    return tuple(parts)


def _parse_bool(s: Any, default: bool = False) -> bool:
    if s is None:
        return default
    if isinstance(s, bool):
        return s
    t = str(s).strip().lower()
    return t in ("1", "true", "yes", "on")


def _parse_float_opt(s: Optional[str]) -> Optional[float]:
    if s is None or str(s).strip() == "":
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class MatchConstraints:
    """召回后重排用的可选约束。"""

    provinces: Tuple[str, ...] = ()
    cities: Tuple[str, ...] = ()
    field_keywords: Tuple[str, ...] = ()
    exclude_ids: Tuple[str, ...] = ()
    hard_region: bool = False
    hard_field: bool = False
    # 低于该召回分（0–100，与检索结果 score 同量纲）的候选剔除；None 表示仅用环境变量 RERANK_MIN_RECALL_SCORE
    min_recall_score: Optional[float] = None
    salary_expectation_note: str = ""

    def to_summary(self) -> dict[str, Any]:
        return {
            "provinces": list(self.provinces),
            "cities": list(self.cities),
            "field_keywords": list(self.field_keywords),
            "exclude_ids": list(self.exclude_ids),
            "hard_region": self.hard_region,
            "hard_field": self.hard_field,
            "min_recall_score": self.min_recall_score,
            "salary_expectation_note": self.salary_expectation_note,
        }

    @classmethod
    def empty(cls) -> MatchConstraints:
        return cls()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MatchConstraints:
        if not d:
            return cls.empty()
        prov = d.get("provinces") or d.get("province") or d.get("preferred_provinces") or []
        cities = d.get("cities") or d.get("city") or d.get("preferred_cities") or []
        fk = (
            d.get("field_keywords")
            or d.get("fields")
            or d.get("keywords")
            or d.get("required_field_keywords")
            or []
        )
        ex = d.get("exclude_ids") or d.get("exclude_enterprise_ids") or []
        if isinstance(ex, str):
            ex = _split_csv(ex)
        if isinstance(prov, str):
            prov = _split_csv(prov)
        if isinstance(cities, str):
            cities = _split_csv(cities)
        if isinstance(fk, str):
            fk = _split_csv(fk)
        note = str(d.get("salary_expectation_note") or d.get("expected_salary_text") or "").strip()
        if not note and d.get("salary_max_wan") not in (None, ""):
            try:
                note = f"期望薪资上限约 {float(d.get('salary_max_wan'))} 万元/年"
            except (TypeError, ValueError):
                note = ""
        mrs = d.get("min_recall_score")
        if mrs is not None and mrs != "":
            try:
                mrs_f: Optional[float] = float(mrs)
            except (TypeError, ValueError):
                mrs_f = None
        else:
            mrs_f = None
        return cls(
            provinces=tuple(str(x).strip() for x in prov if str(x).strip()),
            cities=tuple(str(x).strip() for x in cities if str(x).strip()),
            field_keywords=tuple(str(x).strip() for x in fk if str(x).strip()),
            exclude_ids=tuple(str(x).strip() for x in ex if str(x).strip()),
            hard_region=_parse_bool(d.get("hard_region"), False),
            hard_field=_parse_bool(d.get("hard_field"), False),
            min_recall_score=mrs_f,
            salary_expectation_note=note,
        )

    @classmethod
    def from_json_str(cls, raw: Optional[str]) -> MatchConstraints:
        if not raw or not str(raw).strip():
            return cls.empty()
        try:
            obj = json.loads(str(raw))
        except json.JSONDecodeError:
            return cls.empty()
        if isinstance(obj, dict):
            return cls.from_dict(obj)
        return cls.empty()


def merge_constraints(base: MatchConstraints, overlay: MatchConstraints) -> MatchConstraints:
    """overlay 非空字段覆盖 base（用于 JSON 覆盖表单）。"""
    prov = overlay.provinces if overlay.provinces else base.provinces
    cities = overlay.cities if overlay.cities else base.cities
    fk = overlay.field_keywords if overlay.field_keywords else base.field_keywords
    ex = overlay.exclude_ids if overlay.exclude_ids else base.exclude_ids
    hr = overlay.hard_region or base.hard_region
    hf = overlay.hard_field or base.hard_field
    mrs = overlay.min_recall_score if overlay.min_recall_score is not None else base.min_recall_score
    note = overlay.salary_expectation_note if overlay.salary_expectation_note else base.salary_expectation_note
    return MatchConstraints(
        provinces=prov,
        cities=cities,
        field_keywords=fk,
        exclude_ids=ex,
        hard_region=hr,
        hard_field=hf,
        min_recall_score=mrs,
        salary_expectation_note=note,
    )


def constraints_from_optional_form(
    provinces_csv: Optional[str] = None,
    cities_csv: Optional[str] = None,
    field_keywords_csv: Optional[str] = None,
    exclude_ids_csv: Optional[str] = None,
    hard_region: Optional[str] = None,
    hard_field: Optional[str] = None,
    constraints_json: Optional[str] = None,
    min_recall_score: Optional[str] = None,
    salary_max_wan: Optional[str] = None,
    expected_salary_text: Optional[str] = None,
) -> MatchConstraints:
    """从 Web Form / CLI 字符串构造约束。"""
    note_parts: list[str] = []
    if expected_salary_text and str(expected_salary_text).strip():
        note_parts.append(str(expected_salary_text).strip())
    if salary_max_wan is not None and str(salary_max_wan).strip() != "":
        try:
            note_parts.append(f"期望薪资上限约 {float(str(salary_max_wan).strip())} 万元/年")
        except (TypeError, ValueError):
            pass
    salary_note = "；".join(note_parts)

    c = MatchConstraints(
        provinces=_split_csv(provinces_csv),
        cities=_split_csv(cities_csv),
        field_keywords=_split_csv(field_keywords_csv),
        exclude_ids=_split_csv(exclude_ids_csv),
        hard_region=_parse_bool(hard_region, False),
        hard_field=_parse_bool(hard_field, False),
        min_recall_score=_parse_float_opt(min_recall_score),
        salary_expectation_note=salary_note,
    )
    js = constraints_from_json_str(constraints_json)
    merged = merge_constraints(c, js)
    if not salary_note:
        return merged
    return MatchConstraints(
        provinces=merged.provinces,
        cities=merged.cities,
        field_keywords=merged.field_keywords,
        exclude_ids=merged.exclude_ids,
        hard_region=merged.hard_region,
        hard_field=merged.hard_field,
        min_recall_score=merged.min_recall_score,
        salary_expectation_note=salary_note or merged.salary_expectation_note,
    )


def constraints_from_json_str(raw: Optional[str]) -> MatchConstraints:
    return MatchConstraints.from_json_str(raw)


def parse_constraints_from_form(
    preferred_provinces: str = "",
    preferred_cities: str = "",
    required_field_keywords: str = "",
    exclude_enterprise_ids: str = "",
    hard_region: str = "false",
    hard_field: str = "false",
    constraints_json: Optional[str] = None,
    min_recall_score: str = "",
    salary_max_wan: str = "",
    expected_salary_text: str = "",
) -> MatchConstraints:
    """FastAPI Form 字段名与内部 MatchConstraints 的桥接。"""
    return constraints_from_optional_form(
        provinces_csv=preferred_provinces or None,
        cities_csv=preferred_cities or None,
        field_keywords_csv=required_field_keywords or None,
        exclude_ids_csv=exclude_enterprise_ids or None,
        hard_region=hard_region,
        hard_field=hard_field,
        constraints_json=constraints_json,
        min_recall_score=min_recall_score or None,
        salary_max_wan=salary_max_wan or None,
        expected_salary_text=expected_salary_text or None,
    )
