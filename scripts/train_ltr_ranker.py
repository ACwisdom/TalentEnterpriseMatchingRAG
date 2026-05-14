"""
轻量 LTR：用 sklearn 在带标签特征表上训练二分类器，导出 joblib 供线上 RERANK_WEIGHT_LTR + LTR_INFERENCE_ENABLED 使用。

特征列须与 src/ltr_features.py 中 FEATURE_COLUMNS 一致；示例见 docs/ranking_labels.example.csv。

用法（项目根目录）:
  pip install scikit-learn pandas
  python scripts/train_ltr_ranker.py --csv docs/ranking_labels.example.csv --out models/ltr_ranker.joblib
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="训练轻量 LTR（sklearn joblib）")
    p.add_argument(
        "--csv",
        type=str,
        default=str(root / "docs" / "ranking_labels.example.csv"),
        help="含 label 与特征列的 CSV",
    )
    p.add_argument(
        "--out",
        type=str,
        default=str(root / "models" / "ltr_ranker.joblib"),
        help="输出 joblib 路径（勿提交大文件，models/*.joblib 已 gitignore）",
    )
    p.add_argument("--test-size", type=float, default=0.25, help="留出集比例")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    sys.path.insert(0, str(root))

    import joblib
    import pandas as pd
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split

    from src.ltr_features import FEATURE_COLUMNS

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"CSV 不存在: {csv_path}")
        return 1

    df = pd.read_csv(csv_path)
    if "label" not in df.columns:
        print("CSV 须包含 label 列（0/1）")
        return 1
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        print(f"缺少特征列: {missing}")
        return 1

    X = df[FEATURE_COLUMNS].astype(float).values
    y = df["label"].astype(int).values

    if len(y) < 4:
        print("样本过少，直接全量拟合（无留出报告）")
        clf = GradientBoostingClassifier(random_state=42)
        clf.fit(X, y)
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=42, stratify=y if len(set(y)) > 1 else None
        )
        clf = GradientBoostingClassifier(random_state=42)
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        print(classification_report(y_test, y_pred, digits=3))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out)
    print(f"已保存: {out.resolve()}")
    print("线上启用：设置 LTR_MODEL_PATH 为该路径、LTR_INFERENCE_ENABLED=1、RERANK_WEIGHT_LTR>0。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
