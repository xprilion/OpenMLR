"""Hybrid Search Engine — sparse BM25 + dense vector retrieval for workspace knowledge.

Combines lexical keyword matching (Okapi BM25) and semantic vector search
with Reciprocal Rank Fusion (RRF) and linear weighted score blending.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .vector_index import VectorChunk, VectorIndex

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "ought",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    if remove_stopwords:
        return [w for w in words if w not in STOPWORDS and len(w) > 1]
    return [w for w in words if len(w) > 1]


@dataclass
class BM25Document:
    doc_id: str
    text: str
    tokens: list[str]
    term_frequencies: dict[str, int]
    length: int
    metadata: dict[str, Any] = field(default_factory=dict)


class BM25Index:
    """Okapi BM25 sparse lexical search index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._docs: dict[str, BM25Document] = {}
        self._inverted: dict[str, dict[str, int]] = {}
        self._total_tokens = 0

    def add_document(
        self, doc_id: str, text: str, metadata: dict[str, Any] | None = None
    ) -> BM25Document:
        self.delete_document(doc_id)
        tokens = tokenize(text)
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        doc = BM25Document(
            doc_id=doc_id,
            text=text,
            tokens=tokens,
            term_frequencies=tf,
            length=len(tokens),
            metadata=metadata or {},
        )
        self._docs[doc_id] = doc
        self._total_tokens += doc.length

        for term, count in tf.items():
            if term not in self._inverted:
                self._inverted[term] = {}
            self._inverted[term][doc_id] = count
        return doc

    def delete_document(self, doc_id: str) -> bool:
        doc = self._docs.pop(doc_id, None)
        if not doc:
            return False
        self._total_tokens -= doc.length
        for term in doc.term_frequencies:
            if term in self._inverted:
                self._inverted[term].pop(doc_id, None)
                if not self._inverted[term]:
                    del self._inverted[term]
        return True

    @property
    def avg_doc_len(self) -> float:
        return (self._total_tokens / len(self._docs)) if self._docs else 1.0

    def _idf(self, term: str) -> float:
        n_q = len(self._inverted.get(term, {}))
        if n_q == 0:
            return 0.0
        return math.log((len(self._docs) - n_q + 0.5) / (n_q + 0.5) + 1.0)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[tuple[BM25Document, float]]:
        if not self._docs or not query.strip():
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scores: dict[str, float] = {}
        avgdl = self.avg_doc_len
        for token in q_tokens:
            idf = self._idf(token)
            if idf <= 0.0:
                continue
            for doc_id, tf in self._inverted.get(token, {}).items():
                doc = self._docs[doc_id]
                if filter_metadata and not VectorIndex._matches_filter(
                    doc.metadata, filter_metadata
                ):
                    continue
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc.length / avgdl))
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * ((tf * (self.k1 + 1.0)) / denom)

        ranked = [(self._docs[doc_id], score) for doc_id, score in scores.items()]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": round(self.score, 4),
            "dense_score": round(self.dense_score, 4),
            "sparse_score": round(self.sparse_score, 4),
            "metadata": self.metadata,
        }


def _normalize_scores_map(scores_dict: dict[str, float]) -> dict[str, float]:
    """Normalize score values to [0, 1] range using min-max scaling."""
    if not scores_dict:
        return {}
    vals = list(scores_dict.values())
    mx, mn = max(vals), min(vals)
    if mx == mn:
        return dict.fromkeys(scores_dict, 1.0 if mx > 0 else 0.0)
    diff = mx - mn
    return {k: (v - mn) / diff for k, v in scores_dict.items()}


class HybridSearchEngine:
    """Combines BM25 sparse search and dense vector similarity into hybrid retrieval."""

    def __init__(self, workspace_path: str | Path | None = None, dimension: int = 64):
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.vector_index = VectorIndex(dimension=dimension)
        self.bm25_index = BM25Index()

    def index_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 400,
        chunk_overlap: int = 50,
    ) -> list[VectorChunk]:
        meta = metadata or {}
        self.bm25_index.add_document(doc_id=doc_id, text=text, metadata=meta)
        return self.vector_index.add_document(
            doc_id=doc_id,
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata=meta,
        )

    def delete_document(self, doc_id: str) -> None:
        self.bm25_index.delete_document(doc_id)
        self.vector_index.delete_document(doc_id)

    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5,
        filter_metadata: dict[str, Any] | None = None,
        use_rrf: bool = False,
        rrf_k: int = 60,
    ) -> list[SearchResult]:
        if not query.strip():
            return []

        dense_res = self.vector_index.search(
            query=query, top_k=top_k * 3, filter_metadata=filter_metadata
        )
        sparse_res = self.bm25_index.search(
            query=query, top_k=top_k * 3, filter_metadata=filter_metadata
        )

        if use_rrf:
            return self._fuse_rrf(dense_res, sparse_res, top_k=top_k, rrf_k=rrf_k)
        return self._fuse_linear(dense_res, sparse_res, top_k=top_k, alpha=alpha)

    def _resolve_item_info(self, cid: str) -> tuple[str, str, dict[str, Any]]:
        """Resolve doc_id, text, and metadata for a chunk or document id."""
        chunk = self.vector_index.get_chunk(cid)
        if chunk:
            return chunk.doc_id, chunk.text, chunk.metadata
        doc_id = cid.split("#")[0]
        doc = self.bm25_index._docs.get(doc_id)
        return doc_id, (doc.text if doc else ""), (doc.metadata if doc else {})

    def _fuse_linear(
        self,
        dense_res: list[tuple[VectorChunk, float]],
        sparse_res: list[tuple[BM25Document, float]],
        top_k: int,
        alpha: float,
    ) -> list[SearchResult]:
        dense_map = {chunk.chunk_id: score for chunk, score in dense_res}
        sparse_map = {f"{doc.doc_id}#chunk_0": score for doc, score in sparse_res}

        norm_dense = _normalize_scores_map(dense_map)
        norm_sparse = _normalize_scores_map(sparse_map)

        all_keys = set(norm_dense.keys()) | set(norm_sparse.keys())
        merged: list[SearchResult] = []

        for cid in all_keys:
            d_score = dense_map.get(cid, 0.0)
            s_score = sparse_map.get(cid, 0.0)
            score = alpha * norm_dense.get(cid, 0.0) + (1.0 - alpha) * norm_sparse.get(cid, 0.0)
            doc_id, text, meta = self._resolve_item_info(cid)

            merged.append(
                SearchResult(
                    doc_id=doc_id,
                    chunk_id=cid,
                    text=text,
                    score=score,
                    dense_score=d_score,
                    sparse_score=s_score,
                    metadata=meta,
                )
            )

        merged.sort(key=lambda x: (x.score, x.sparse_score + x.dense_score), reverse=True)
        return merged[:top_k]

    def _fuse_rrf(
        self,
        dense_res: list[tuple[VectorChunk, float]],
        sparse_res: list[tuple[BM25Document, float]],
        top_k: int,
        rrf_k: int,
    ) -> list[SearchResult]:
        rrf_map: dict[str, dict[str, Any]] = {}

        for rank, (chunk, d_score) in enumerate(dense_res, start=1):
            cid = chunk.chunk_id
            rrf_map[cid] = {
                "doc_id": chunk.doc_id,
                "chunk_id": cid,
                "text": chunk.text,
                "score": 1.0 / (rrf_k + rank),
                "dense_score": d_score,
                "sparse_score": 0.0,
                "metadata": chunk.metadata,
            }

        for rank, (doc, s_score) in enumerate(sparse_res, start=1):
            cid = f"{doc.doc_id}#chunk_0"
            if cid not in rrf_map:
                rrf_map[cid] = {
                    "doc_id": doc.doc_id,
                    "chunk_id": cid,
                    "text": doc.text,
                    "score": 0.0,
                    "dense_score": 0.0,
                    "sparse_score": s_score,
                    "metadata": doc.metadata,
                }
            rrf_map[cid]["sparse_score"] = s_score
            rrf_map[cid]["score"] += 1.0 / (rrf_k + rank)

        ranked_items = [
            SearchResult(
                doc_id=v["doc_id"],
                chunk_id=v["chunk_id"],
                text=v["text"],
                score=v["score"],
                dense_score=v["dense_score"],
                sparse_score=v["sparse_score"],
                metadata=v["metadata"],
            )
            for v in rrf_map.values()
        ]
        ranked_items.sort(key=lambda x: x.score, reverse=True)
        return ranked_items[:top_k]

    def save_index(self, directory: str | Path | None = None) -> None:
        target_dir = Path(
            directory or (self.workspace_path / ".project-meta" if self.workspace_path else ".")
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        self.vector_index.save_to_file(target_dir / "vector_index.json")

        bm25_data = {
            "version": 1,
            "total_docs": len(self.bm25_index._docs),
            "docs": [
                {"doc_id": d.doc_id, "text": d.text, "metadata": d.metadata}
                for d in self.bm25_index._docs.values()
            ],
        }
        (target_dir / "bm25_index.json").write_text(
            json.dumps(bm25_data, indent=2), encoding="utf-8"
        )

    def load_index(self, directory: str | Path | None = None) -> bool:
        target_dir = Path(
            directory or (self.workspace_path / ".project-meta" if self.workspace_path else ".")
        )
        vec_loaded = self.vector_index.load_from_file(target_dir / "vector_index.json")
        bm25_loaded = False

        bm25_path = target_dir / "bm25_index.json"
        if bm25_path.exists():
            try:
                data = json.loads(bm25_path.read_text(encoding="utf-8"))
                for item in data.get("docs", []):
                    self.bm25_index.add_document(
                        doc_id=item["doc_id"],
                        text=item["text"],
                        metadata=item.get("metadata", {}),
                    )
                bm25_loaded = True
            except Exception as e:
                logger.warning(f"Failed to load BM25 index: {e}")

        return vec_loaded or bm25_loaded
