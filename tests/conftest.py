"""pytest 全局：默认关闭 CrossEncoder 以免 CI 下载大模型。"""
import os

os.environ.setdefault("RERANK_ENABLED", "0")
