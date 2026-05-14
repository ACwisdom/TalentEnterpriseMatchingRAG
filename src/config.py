"""
配置文件 - 人才-企业匹配RAG系统
"""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ============ API配置 ============
# MiMo-V2.5-Pro API配置
# 密钥：环境变量 MIMO_API_KEY，或项目根目录 .env（勿提交 .env）
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
# 小米 MiMo OpenAI 兼容接口（完整 chat 路径）
MIMO_API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MIMO_MODEL = "mimo-v2.5-pro"
# 多模态模型配置（用于分析微信截图等图像）
MIMO_MULTIMODAL_MODEL = "mimo-v2.5"  # 多模态版本
MIMO_MULTIMODAL_API_URL = "https://api.xiaomimimo.com/v1/chat/completions"  # 同一端点
# OpenAI 兼容：使用标准 Bearer（见 llm_client._build_headers）
MIMO_API_KEY_HEADER = "Authorization"

# ============ 向量数据库配置 ============
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "enterprise_vectors")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ENTERPRISE_COLLECTION_NAME = os.getenv("ENTERPRISE_COLLECTION_NAME", "enterprises")

# ============ 检索配置 ============
TOP_K = 15  # 召回企业数量
SCORE_THRESHOLD = 0.7  # 相似度阈值（0-1）

# keyword | vector | hybrid | hybrid_legacy（全库向量 + 并行 RRF，兼容旧行为）
_RETRIEVAL = os.getenv("RETRIEVAL_MODE", "hybrid").strip().lower()
RETRIEVAL_MODE = (
    _RETRIEVAL
    if _RETRIEVAL in ("keyword", "vector", "hybrid", "hybrid_legacy")
    else "hybrid"
)
HYBRID_VECTOR_POOL = int(os.getenv("HYBRID_VECTOR_POOL", "30"))
LAYER1_CANDIDATE_CAP = int(os.getenv("LAYER1_CANDIDATE_CAP", "500"))
RRF_K = int(os.getenv("RRF_K", "60"))
RESUME_EMBED_CHUNK_CHARS = int(os.getenv("RESUME_EMBED_CHUNK_CHARS", "320"))
RESUME_EMBED_CHUNK_STRIDE = int(os.getenv("RESUME_EMBED_CHUNK_STRIDE", "240"))
EMBED_QUERY_MAX_CHARS = int(os.getenv("EMBED_QUERY_MAX_CHARS", "24000"))
AUTO_REBUILD_STALE_INDEX = os.getenv("AUTO_REBUILD_STALE_INDEX", "0").strip() in ("1", "true", "yes")

# ============ 宽召回 + 重排（CrossEncoder / 规则 / 可选 LTR）============
# 检索阶段先取 min(RECALL_TOP_CAP, max(round(top_k * RECALL_TOP_MULTIPLIER), top_k)) 条，再重排截断到 top_k
RECALL_TOP_MULTIPLIER = float(os.getenv("RECALL_TOP_MULTIPLIER", "3"))
RECALL_TOP_CAP = int(os.getenv("RECALL_TOP_CAP", "120"))

# 关闭后仅按检索分 + 规则/LTR 权重融合（不加载 CrossEncoder）
_RERANK_EN = os.getenv("RERANK_ENABLED", "1").strip().lower()
RERANK_ENABLED = _RERANK_EN not in ("0", "false", "no", "off")

# 默认 BAAI/bge-reranker-v2-m3：多语种（含中文）句对打分；首次从 Hub 拉取权重约 2GB+（以实际缓存为准）。
# 兼容旧变量名 CROSS_ENCODER_MODEL。
RERANK_CROSS_ENCODER_MODEL = (
    os.getenv("RERANK_CROSS_ENCODER_MODEL") or os.getenv("CROSS_ENCODER_MODEL") or "BAAI/bge-reranker-v2-m3"
).strip()
RERANK_BATCH_SIZE = int(os.getenv("RERANK_BATCH_SIZE", "16"))
RERANK_RESUME_MAX_CHARS = max(512, int(os.getenv("RERANK_RESUME_MAX_CHARS", "8000")))
RERANK_ENTERPRISE_MAX_CHARS = max(256, int(os.getenv("RERANK_ENTERPRISE_MAX_CHARS", "4000")))
RERANK_WEIGHT_RECALL = float(os.getenv("RERANK_WEIGHT_RECALL", "0.35"))
RERANK_WEIGHT_CE = float(os.getenv("RERANK_WEIGHT_CE", "0.55"))
RERANK_WEIGHT_RULE = float(os.getenv("RERANK_WEIGHT_RULE", "0.10"))
RERANK_WEIGHT_LTR = float(os.getenv("RERANK_WEIGHT_LTR", "0.0"))
RERANK_MIN_RECALL_SCORE = float(os.getenv("RERANK_MIN_RECALL_SCORE", "0"))

# LTR：训练见 scripts/train_ltr_ranker.py；存在模型且开启推理时参与融合
LTR_MODEL_PATH = os.getenv("LTR_MODEL_PATH", "").strip()
_LTR_INF = os.getenv("LTR_INFERENCE_ENABLED", "0").strip().lower()
LTR_INFERENCE_ENABLED = _LTR_INF in ("1", "true", "yes", "on")

# Markdown 报告分档（与综合 score 一致）
MATCH_SCORE_HIGH = float(os.getenv("MATCH_SCORE_HIGH", "70"))
MATCH_SCORE_MID = float(os.getenv("MATCH_SCORE_MID", "40"))

# 索引用文档：加权叙事模板（true）或沿用扁平 enterprise_to_document（false）
_USE_WIDX = os.getenv("USE_WEIGHTED_INDEX_DOC", "1").strip().lower()
USE_WEIGHTED_INDEX_DOC = _USE_WIDX in ("1", "true", "yes", "weighted")
_INDEX_STYLE = os.getenv("INDEX_DOC_STYLE", "").strip().lower()
if _INDEX_STYLE == "flat":
    USE_WEIGHTED_INDEX_DOC = False
elif _INDEX_STYLE == "weighted":
    USE_WEIGHTED_INDEX_DOC = True

# 可选术语表：增强简历关键词抽取（每行一词，# 开头为注释）
def _default_tech_lexicon_path() -> str:
    for rel in ("data/tech_lexicon.txt", "src/tech_lexicon.txt"):
        p = _PROJECT_ROOT / rel
        if p.is_file():
            return str(p)
    return str(_PROJECT_ROOT / "data" / "tech_lexicon.txt")


if os.getenv("TECH_LEXICON_PATH") is not None and str(os.getenv("TECH_LEXICON_PATH", "")).strip() != "":
    TECH_LEXICON_PATH: str = str(os.getenv("TECH_LEXICON_PATH")).strip()
else:
    TECH_LEXICON_PATH = _default_tech_lexicon_path()

# LLM 提示：参考日期（用于时效性表述，默认当天）
_rd = os.getenv("REFERENCE_DATE", "").strip()
if _rd:
    try:
        REFERENCE_DATE = date.fromisoformat(_rd)
    except ValueError:
        REFERENCE_DATE = date.today()
else:
    REFERENCE_DATE = date.today()

# ============ 文件路径配置 ============
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTERPRISE_EXCEL = os.path.join(PROJECT_ROOT, "data", "enterprise_db.xlsx")
SYSTEM_PROMPT_FILE = os.path.join(PROJECT_ROOT, "prompts", "system_prompt.txt")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")

# 原始资料路径（只读）
DATA_DIR = os.path.join(PROJECT_ROOT, "资料")
ENTERPRISE_EXCEL_SRC = os.path.join(DATA_DIR, "RAG", "企业库", "沃咨企业库1.0.xlsx")

# ============ 企业库字段配置 ============
ENTERPRISE_FIELDS = [
    "省",
    "市", 
    "区/县",
    "地区门槛",
    "企业名称",
    "一级领域",
    "二级领域",
    "企业主要产品",
    "政府给介绍",
    "企业官方/第三方/新闻介绍"
]

# ============ 日志配置 ============
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(PROJECT_ROOT, "rag_system.log")
