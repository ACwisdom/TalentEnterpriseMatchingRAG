"""
企业向量索引：Chroma 持久化 + sentence-transformers 嵌入。
支持索引清单（Excel mtime/size）、空库自动构建、简历切块均值查询向量。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import (
    AUTO_REBUILD_STALE_INDEX,
    CHROMA_PERSIST_DIR,
    EMBED_QUERY_MAX_CHARS,
    EMBEDDING_MODEL,
    ENTERPRISE_COLLECTION_NAME,
    ENTERPRISE_EXCEL,
    RESUME_EMBED_CHUNK_CHARS,
    RESUME_EMBED_CHUNK_STRIDE,
    TOP_K,
    USE_WEIGHTED_INDEX_DOC,
)
from src.data_processor import load_enterprise_db, prepare_documents

_CHROMA_META_KEYS = [
    "企业名称",
    "省",
    "市",
    "区/县",
    "地区门槛",
    "一级领域",
    "二级领域",
    "企业主要产品",
]


def _manifest_path(persist_dir: str) -> str:
    return os.path.join(persist_dir, "index_manifest.json")


def _excel_fingerprint(excel_path: str) -> Dict[str, Any]:
    st = os.stat(excel_path)
    return {
        "excel_path": os.path.abspath(excel_path),
        "mtime": st.st_mtime,
        "size": st.st_size,
    }


def _truncate_str(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _narrow_metadata_for_chroma(full_meta: Dict[str, Any], enterprise_id: str) -> Dict[str, str]:
    out: Dict[str, str] = {"enterprise_id": str(enterprise_id)}
    for k in _CHROMA_META_KEYS:
        out[k] = _truncate_str(str(full_meta.get(k, "")), 480)
    return out


def chunk_resume_text(
    text: str,
    chunk_chars: int = None,
    stride: int = None,
    max_chars: int = None,
) -> List[str]:
    chunk_chars = chunk_chars or RESUME_EMBED_CHUNK_CHARS
    stride = stride or RESUME_EMBED_CHUNK_STRIDE
    max_chars = max_chars or EMBED_QUERY_MAX_CHARS
    text = (text or "")[:max_chars]
    if not text.strip():
        return [" "]
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        piece = text[i : i + chunk_chars]
        if piece.strip():
            chunks.append(piece)
        i += stride
        if i >= n and not chunks:
            chunks.append(text[:chunk_chars] if text else " ")
            break
    if not chunks:
        chunks = [text[:chunk_chars] or " "]
    return chunks


class EnterpriseVectorIndex:
    """企业库向量索引与查询（手动提供 embedding，不依赖 Chroma 内置 embedding）。"""

    def __init__(self, excel_path: Optional[str] = None, persist_dir: Optional[str] = None):
        self.excel_path = excel_path or ENTERPRISE_EXCEL
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        self._model = None
        self._client = None
        self._collection = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def _get_client(self):
        if self._client is None:
            import chromadb

            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._get_client().get_or_create_collection(
                name=ENTERPRISE_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _reset_collection(self) -> None:
        client = self._get_client()
        try:
            client.delete_collection(ENTERPRISE_COLLECTION_NAME)
        except Exception:
            pass
        self._collection = None

    def _read_manifest(self) -> Optional[Dict[str, Any]]:
        path = _manifest_path(self.persist_dir)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _write_manifest(self, num_rows: int) -> None:
        os.makedirs(self.persist_dir, exist_ok=True)
        fp = _excel_fingerprint(self.excel_path)
        fp["embedding_model"] = EMBEDDING_MODEL
        fp["use_weighted_index_doc"] = USE_WEIGHTED_INDEX_DOC
        fp["num_rows"] = num_rows
        with open(_manifest_path(self.persist_dir), "w", encoding="utf-8") as f:
            json.dump(fp, f, ensure_ascii=False, indent=2)

    def _manifest_stale_reason(self) -> Optional[str]:
        if not os.path.isfile(self.excel_path):
            return "Excel 不存在"
        manifest = self._read_manifest()
        if not manifest:
            return "无索引清单"
        cur = _excel_fingerprint(self.excel_path)
        if manifest.get("excel_path") != cur["excel_path"]:
            return "Excel 路径变更"
        if manifest.get("mtime") != cur["mtime"] or manifest.get("size") != cur["size"]:
            return "Excel 已更新（mtime/size 不一致）"
        if manifest.get("embedding_model") != EMBEDDING_MODEL:
            return "嵌入模型变更"
        if manifest.get("use_weighted_index_doc") != USE_WEIGHTED_INDEX_DOC:
            return "索引入库文档模板变更（USE_WEIGHTED_INDEX_DOC / INDEX_DOC_STYLE）"
        return None

    def collection_count(self) -> int:
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def ensure_index(self) -> None:
        if self.collection_count() == 0:
            print("📇 向量库为空，正在从企业 Excel 构建索引（首次较慢）…")
            self.build(force=False)
            return
        reason = self._manifest_stale_reason()
        if reason:
            msg = f"⚠️ 向量索引可能过期：{reason}。可运行 python -m src.build_enterprise_index --force 重建。"
            print(msg)
            if AUTO_REBUILD_STALE_INDEX:
                print("AUTO_REBUILD_STALE_INDEX=1，正在强制重建向量索引…")
                self.build(force=True)

    def build(self, force: bool = False) -> int:
        if not os.path.isfile(self.excel_path):
            raise FileNotFoundError(f"企业库不存在: {self.excel_path}")
        n_existing = self.collection_count()
        if force:
            self._reset_collection()
        elif n_existing > 0:
            if self._manifest_stale_reason() is None:
                print("向量索引已存在且与 Excel 指纹一致，跳过构建。")
                return n_existing
            print(f"向量索引需重建：{self._manifest_stale_reason()}。请运行 python -m src.build_enterprise_index --force")
            return n_existing
        col = self._get_collection()
        enterprises = load_enterprise_db(self.excel_path)
        documents, metadatas, ids = prepare_documents(enterprises)
        chroma_metas: List[Dict[str, str]] = []
        for mid, meta in zip(ids, metadatas):
            chroma_metas.append(_narrow_metadata_for_chroma(meta, mid))
        model = self._get_model()
        embeddings = model.encode(
            documents,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        if hasattr(embeddings, "tolist"):
            emb_list = embeddings.tolist()
        else:
            emb_list = np.asarray(embeddings).tolist()
        col.add(ids=ids, documents=documents, metadatas=chroma_metas, embeddings=emb_list)
        self._write_manifest(len(ids))
        print(f"✅ 向量索引已写入 {len(ids)} 条，持久化目录: {self.persist_dir}")
        return len(ids)

    def _encode_query_mean(self, resume_text: str) -> np.ndarray:
        chunks = chunk_resume_text(resume_text)
        model = self._get_model()
        embs = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
        arr = np.asarray(embs, dtype=np.float32)
        q = arr.mean(axis=0)
        norm = np.linalg.norm(q) + 1e-12
        q = q / norm
        return q.astype(np.float32)

    def search(self, resume_text: str, top_k: int = None) -> List[Dict[str, Any]]:
        self.ensure_index()
        top_k = top_k or TOP_K
        q = self._encode_query_mean(resume_text)
        col = self._get_collection()
        res = col.query(
            query_embeddings=[q.tolist()],
            n_results=min(top_k, max(1, col.count())),
            include=["documents", "metadatas", "distances"],
        )
        ids_out = res["ids"][0] if res.get("ids") else []
        docs = res["documents"][0] if res.get("documents") else []
        metas = res["metadatas"][0] if res.get("metadatas") else []
        dists = res["distances"][0] if res.get("distances") else []
        results: List[Dict[str, Any]] = []
        for rank, (eid, doc, meta, dist) in enumerate(zip(ids_out, docs, metas, dists)):
            results.append(self._hit_dict(eid, doc, meta, dist, rank))
        return results

    def _hit_dict(
        self,
        eid: str,
        doc: Optional[str],
        meta: Optional[Dict[str, Any]],
        dist: Any,
        rank: int,
    ) -> Dict[str, Any]:
        try:
            d = float(dist)
        except (TypeError, ValueError):
            d = 1.0
        sim = max(0.0, min(1.0, 1.0 - d))
        score = round(100.0 * sim, 2)
        meta = meta or {}
        md = {k: (meta.get(k, "") or "") for k in _CHROMA_META_KEYS}
        md["enterprise_id"] = str(meta.get("enterprise_id", eid))
        return {
            "content": doc or "",
            "metadata": md,
            "score": score,
            "matched_keywords": ["[向量]"],
            "vector_distance": d,
            "vector_rank": rank,
        }

    def search_subset(
        self,
        resume_text: str,
        candidate_ids: List[str],
        top_k: int = None,
    ) -> List[Dict[str, Any]]:
        """
        仅在 candidate_ids 子集上做向量相似度检索。
        优先使用 Chroma metadata filter（enterprise_id $in）；失败则本地余弦（已归一化嵌入点积）。
        """
        self.ensure_index()
        top_k = top_k or TOP_K
        cand = [str(x).strip() for x in (candidate_ids or []) if str(x).strip()]
        if not cand:
            return self.search(resume_text, top_k=top_k)

        col = self._get_collection()
        n = min(top_k, max(1, len(cand)))
        q = self._encode_query_mean(resume_text)
        q_list = q.tolist()

        try:
            res = col.query(
                query_embeddings=[q_list],
                n_results=min(n, col.count()),
                where={"enterprise_id": {"$in": cand}},
                include=["documents", "metadatas", "distances"],
            )
            ids_out = res["ids"][0] if res.get("ids") else []
            if ids_out:
                docs = res["documents"][0] if res.get("documents") else []
                metas = res["metadatas"][0] if res.get("metadatas") else []
                dists = res["distances"][0] if res.get("distances") else []
                return [
                    self._hit_dict(eid, doc, meta, dist, rank)
                    for rank, (eid, doc, meta, dist) in enumerate(zip(ids_out, docs, metas, dists))
                ]
        except Exception:
            pass

        got = col.get(ids=cand, include=["embeddings", "documents", "metadatas"])
        got_ids = got.get("ids") or []
        embs = got.get("embeddings")
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        if not got_ids or embs is None or len(embs) == 0:
            return []
        mat = np.asarray(embs, dtype=np.float32)
        sims = mat @ q
        order = np.argsort(-sims)
        take = order[: min(n, len(order))]
        results: List[Dict[str, Any]] = []
        for rank, idx in enumerate(take):
            i = int(idx)
            eid = str(got_ids[i])
            doc = docs[i] if i < len(docs) else ""
            meta = metas[i] if i < len(metas) else {}
            d = 1.0 - float(sims[i])
            results.append(self._hit_dict(eid, doc, meta, d, rank))
        return results

    def search_with_expansion(self, resume_text: str, top_k: int = 15) -> List[Dict[str, Any]]:
        results = self.search(resume_text, top_k=top_k)
        if len(results) < 8 and self.collection_count() > top_k:
            results = self.search(resume_text, top_k=min(top_k * 2, self.collection_count()))
        return results[:top_k]

    def get_info(self) -> Dict[str, Any]:
        return {
            "企业数量": self.collection_count(),
            "检索方式": "vector",
            "数据来源": self.excel_path,
            "向量目录": self.persist_dir,
            "嵌入模型": EMBEDDING_MODEL,
        }
