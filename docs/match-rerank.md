# 召回后重排与匹配约束

## 行为说明

1. **扩大召回**：内部 `search_with_expansion` 的 `top_k` 取 `min(RECALL_TOP_CAP, max(用户 top_k, round(用户 top_k × RECALL_TOP_MULTIPLIER)))`，再经 `rerank_enterprises` 截断为用户请求的 `top_k`。
2. **综合分**：每条企业的 `score` 为加权融合后的 0–100 分；`ranking` 含召回分、CrossEncoder 归一化分、规则 bonus、可选 LTR；`ranking_reasons` 为简短中文解释。
3. **交叉编码器**：默认 `RERANK_CROSS_ENCODER_MODEL` = `BAAI/bge-reranker-v2-m3`（也可用环境变量 `CROSS_ENCODER_MODEL` 覆盖）。首次运行会从 Hub 下载权重。关闭：`RERANK_ENABLED=0`（不加载 CE，融合中 CE 权重置零）。
4. **薪资**：企业库无薪资列；表单或 JSON 中的薪资说明写入 `salary_expectation_note`，仅在 `ranking_reasons` 中提示，不做硬性比对。

## 环境变量（节选）

| 变量 | 含义 | 默认 |
|------|------|------|
| `RECALL_TOP_MULTIPLIER` | 召回倍数 | 3 |
| `RECALL_TOP_CAP` | 召回上限 | 120 |
| `RERANK_ENABLED` | 是否启用 CE | 1 |
| `RERANK_CROSS_ENCODER_MODEL` / `CROSS_ENCODER_MODEL` | CrossEncoder 模型名 | BAAI/bge-reranker-v2-m3 |
| `RERANK_BATCH_SIZE` | CE 批大小 | 16 |
| `RERANK_WEIGHT_RECALL` / `RERANK_WEIGHT_CE` / `RERANK_WEIGHT_RULE` / `RERANK_WEIGHT_LTR` | 融合权重（归一化） | 0.35 / 0.55 / 0.10 / 0.0 |
| `RERANK_MIN_RECALL_SCORE` | 最低召回分过滤（0 表示关闭） | 0 |
| `LTR_MODEL_PATH` | joblib 模型路径 | 空 |
| `LTR_INFERENCE_ENABLED` | 是否加载 LTR 模型 | 0 |
| `MATCH_SCORE_HIGH` / `MATCH_SCORE_MID` | Markdown 分档阈值 | 70 / 40 |

## Web / Form

可选字段：`preferred_provinces`、`preferred_cities`、`required_field_keywords`、`exclude_enterprise_ids`、`hard_region`、`hard_field`、`min_recall_score`、`salary_max_wan`、`expected_salary_text`、`constraints_json`（JSON 与表单合并）。

## 轻量 LTR 训练

特征列与 `src/ltr_features.py` 中 `FEATURE_COLUMNS` 一致；示例数据见 [ranking_labels.example.csv](ranking_labels.example.csv)。

```bash
pip install scikit-learn pandas
python scripts/train_ltr_ranker.py --csv docs/ranking_labels.example.csv --out models/ltr_ranker.joblib
```

线上启用：设置 `LTR_MODEL_PATH` 为上述文件、`LTR_INFERENCE_ENABLED=1`，并将 `RERANK_WEIGHT_LTR` 调到大于 0（同时相应调低其他权重之和以保持可解释性）。
