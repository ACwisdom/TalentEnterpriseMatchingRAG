"""
批量生成人才-企业匹配报告（Word + JSON）。

默认「全量」体验（推荐）：
  - 检索：RETRIEVAL_MODE=hybrid（第一层：二级领域+主要产品关键词漏斗；第二层：子集向量；RRF 融合）。
    hybrid_legacy=旧版全库向量+RRF。索引用加权文档变更后请执行：python -m src.build_enterprise_index --force
  - Prompt：注入 REFERENCE_DATE（可用环境变量固定）与在职/全职适配说明。
  - 报告与画像：调用 MiMo（需 MIMO_API_KEY，失败时降级为格式化文本）

轻量模式（--light）：仅关键词检索 + 无大模型，仅适合 CI/离线冒烟，不适合对外展示。

用法（在项目根目录）:
  python scripts/run_match_reports.py
  python scripts/run_match_reports.py --light
  python scripts/run_match_reports.py --provinces 江苏 --hard-region --min-recall-score 20
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="生成匹配报告（默认全量：hybrid + MiMo）")
    p.add_argument(
        "--light",
        action="store_true",
        help="轻量：关键词检索 + 不调 MiMo（展示质量差，仅调试用）",
    )
    p.add_argument(
        "--retrieval",
        choices=("keyword", "vector", "hybrid", "hybrid_legacy"),
        default=None,
        help="覆盖 RETRIEVAL_MODE（默认全量时为 hybrid；与 --light 互斥时以 --light 为准）",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=str(root / "data" / "output"),
        help="输出目录",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="召回企业数（建议 12～20，便于 LLM 写足分析）",
    )
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="不调 MiMo 写主报告（仍可用 hybrid 检索）",
    )
    p.add_argument(
        "--no-profile",
        action="store_true",
        help="不调 MiMo 生成人才画像摘要",
    )
    p.add_argument(
        "--prebuild-index",
        action="store_true",
        help="先全量重建向量索引再跑简历（等价于 python -m src.build_enterprise_index --force）",
    )
    p.add_argument(
        "--stable-names",
        action="store_true",
        help="输出固定为「简历名_匹配报告.docx」（若文件正被 Word 打开可能保存失败）",
    )
    p.add_argument(
        "--constraints-json",
        type=str,
        default=None,
        help="匹配约束 JSON 文件路径（可选），与下方 CLI 约束合并（后者优先覆盖空项）",
    )
    p.add_argument("--provinces", type=str, default=None, help="期望省份，逗号分隔")
    p.add_argument("--cities", type=str, default=None, help="期望城市，逗号分隔")
    p.add_argument("--field-keywords", type=str, default=None, dest="field_keywords", help="领域关键词，逗号分隔")
    p.add_argument("--exclude-ids", type=str, default=None, dest="exclude_ids", help="排除 enterprise_id，逗号分隔")
    p.add_argument("--hard-region", action="store_true", help="地域硬过滤")
    p.add_argument("--hard-field", action="store_true", help="领域硬过滤")
    p.add_argument("--min-recall-score", type=str, default=None, dest="min_recall_score", help="最低召回分阈值")
    p.add_argument(
        "inputs",
        nargs="*",
        default=[
            str(root / "data" / "input" / "WZ-00003105王明华博士简历.docx"),
            str(root / "data" / "input" / "WZ-A-01.pdf"),
        ],
        help="简历文件路径（可多个）",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    sys.path.insert(0, str(root))

    if args.light:
        os.environ["RETRIEVAL_MODE"] = "keyword"
        use_llm = False
        use_profile = False
    else:
        if args.retrieval:
            os.environ["RETRIEVAL_MODE"] = args.retrieval
        else:
            os.environ.setdefault("RETRIEVAL_MODE", "hybrid")
        use_llm = not args.no_llm
        use_profile = not args.no_profile

    if args.prebuild_index and not args.light:
        from src.enterprise_vector_index import EnterpriseVectorIndex

        print("预构建向量索引…")
        EnterpriseVectorIndex().build(force=True)

    from src.match_constraints import MatchConstraints, constraints_from_optional_form, merge_constraints

    base = constraints_from_optional_form(
        provinces_csv=args.provinces,
        cities_csv=args.cities,
        field_keywords_csv=args.field_keywords,
        exclude_ids_csv=args.exclude_ids,
        hard_region="true" if args.hard_region else "false",
        hard_field="true" if args.hard_field else "false",
        constraints_json=None,
        min_recall_score=args.min_recall_score,
    )
    constraints = base
    if args.constraints_json:
        cp = Path(args.constraints_json)
        if cp.is_file():
            import json

            overlay = MatchConstraints.from_dict(json.loads(cp.read_text(encoding="utf-8")))
            constraints = merge_constraints(base, overlay)
        else:
            print(f"[警告] 约束文件不存在，忽略: {cp}")

    from src.resume_processor import process_resume_and_match

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 60)
    print("匹配报告批量生成")
    print(f"  检索模式: {os.environ.get('RETRIEVAL_MODE', 'hybrid')}")
    print(f"  MiMo 主报告: {use_llm}  人才画像: {use_profile}")
    print(f"  top_k: {args.top_k}")
    print(f"  匹配约束: {constraints.to_summary()}")
    print(f"  输出目录: {out_dir}")
    print("=" * 60)

    for fp in args.inputs:
        path = Path(fp)
        if not path.is_file():
            print(f"[跳过] 文件不存在: {path}")
            continue
        print(f"\n>>> 处理: {path}")
        tag = None if args.stable_names else datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        process_resume_and_match(
            str(path.resolve()),
            output_dir=out_dir,
            top_k=args.top_k,
            use_llm=use_llm,
            use_llm_for_profile=use_profile,
            output_tag=tag,
            constraints=constraints,
        )

    print("\n全部完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
