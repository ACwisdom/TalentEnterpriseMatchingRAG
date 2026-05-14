"""
构建 / 重建企业向量索引（Chroma）。

用法:
  python -m src.build_enterprise_index
  python -m src.build_enterprise_index --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.enterprise_vector_index import EnterpriseVectorIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="构建企业向量索引")
    parser.add_argument("--force", action="store_true", help="删除旧集合并全量重建")
    parser.add_argument("--excel", default=None, help="企业 Excel 路径（默认 config.ENTERPRISE_EXCEL）")
    parser.add_argument("--persist", default=None, help="Chroma 持久化目录（默认 config.CHROMA_PERSIST_DIR）")
    args = parser.parse_args()
    idx = EnterpriseVectorIndex(excel_path=args.excel, persist_dir=args.persist)
    n = idx.build(force=args.force)
    print(f"完成，当前集合文档数: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
