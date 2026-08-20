"""Vector Index — dense semantic vector storage and similarity search.

Provides lightweight, in-memory and persistent vector indexing for project knowledge,
downloaded papers, research notes, and workspace documents.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default vector dimension for deterministic fallback embeddings
DEFAULT_EMBEDDING_DIM = 64


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns 0.0 if vectors are empty or either vector has zero magnitude.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0

    return dot / (norm_a * norm_b)


def generate_deterministic_embedding(text: str, dim: int = DEFAULT_EMBEDDING_DIM) -> list[float]:
    """Generate a normalized pseudo-semantic embedding vector from text.

    Uses sha256 token hashing with position-weighted n-grams as a robust,
    deterministic fallback when external neural embedding models are offline.
    """
    if not text or not text.strip():
        return [0.0] * dim

    vec = [0.0] * dim
    tokens = text.lower().split()
    if not tokens:
        return [0.0] * dim

    for i, token in enumerate(tokens):
        # 1-gram hash
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        pos = h % dim
        weight = 1.0 / math.log2(i + 2.0)
        vec[pos] += weight

        # 2-gram hash if next token exists
        if i + 1 < len(tokens):
            bigram = f"{token}_{tokens[i + 1]}"
            bh = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
            bpos = bh % dim
            vec[bpos] += weight * 1.5

    # Normalize vector to unit length
    magnitude = math.sqrt(sum(x * x for x in vec))
    if magnitude > 1e-12:
        vec = [x / magnitude for x in vec]

    return vec


@dataclass
class VectorChunk:
    """A semantic text chunk with an embedding and metadata."""

    chunk_id: str
    doc_id: str
    text: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VectorChunk:
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            text=data.get("text", ""),
            vector=data.get("vector", []),
            metadata=data.get("metadata", {}),
        )


class VectorIndex:
    """In-memory dense vector index with JSON persistence and metadata filtering."""

    def __init__(
        self,
        dimension: int = DEFAULT_EMBEDDING_DIM,
        embedding_fn: Callable[[str], list[float]] | None = None,
    ):
        self.dimension = dimension
        self.embedding_fn = embedding_fn or (
            lambda t: generate_deterministic_embedding(t, dim=self.dimension)
        )
        self._chunks: dict[str, VectorChunk] = {}
        self._doc_to_chunks: dict[str, set[str]] = {}

    def add_chunk(self, chunk: VectorChunk) -> None:
        """Add a single pre-embedded vector chunk."""
        self._chunks[chunk.chunk_id] = chunk
        if chunk.doc_id not in self._doc_to_chunks:
            self._doc_to_chunks[chunk.doc_id] = set()
        self._doc_to_chunks[chunk.doc_id].add(chunk.chunk_id)

    def add_text_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        vector: list[float] | None = None,
    ) -> VectorChunk:
        """Embed and index a text chunk."""
        vec = vector if vector is not None else self.embedding_fn(text)
        chunk = VectorChunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=text,
            vector=vec,
            metadata=metadata or {},
        )
        self.add_chunk(chunk)
        return chunk

    def add_document(
        self,
        doc_id: str,
        text: str,
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> list[VectorChunk]:
        """Split a document into overlapping chunks, embed them, and index."""
        self.delete_document(doc_id)
        words = text.split()
        if not words:
            return []

        chunks: list[VectorChunk] = []
        step = max(1, chunk_size - chunk_overlap)
        chunk_idx = 0

        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunk_id = f"{doc_id}#chunk_{chunk_idx}"
            chunk_meta = dict(metadata or {})
            chunk_meta["chunk_index"] = chunk_idx
            chunk_meta["total_words"] = len(chunk_words)

            chunk = self.add_text_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=chunk_text,
                metadata=chunk_meta,
            )
            chunks.append(chunk)
            chunk_idx += 1

            if i + chunk_size >= len(words):
                break

        return chunks

    def delete_document(self, doc_id: str) -> int:
        """Remove all indexed chunks for a document ID. Returns count deleted."""
        chunk_ids = self._doc_to_chunks.pop(doc_id, set())
        for cid in chunk_ids:
            self._chunks.pop(cid, None)
        return len(chunk_ids)

    def delete_chunk(self, chunk_id: str) -> bool:
        """Remove a single chunk by ID."""
        chunk = self._chunks.pop(chunk_id, None)
        if chunk:
            doc_chunks = self._doc_to_chunks.get(chunk.doc_id)
            if doc_chunks:
                doc_chunks.discard(chunk_id)
                if not doc_chunks:
                    self._doc_to_chunks.pop(chunk.doc_id, None)
            return True
        return False

    def get_chunk(self, chunk_id: str) -> VectorChunk | None:
        """Retrieve a chunk by ID."""
        return self._chunks.get(chunk_id)

    def get_document_chunks(self, doc_id: str) -> list[VectorChunk]:
        """Retrieve all chunks belonging to a document."""
        chunk_ids = self._doc_to_chunks.get(doc_id, set())
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    def search_by_vector(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        min_similarity: float = -1.0,
    ) -> list[tuple[VectorChunk, float]]:
        """Find the top-k most similar chunks for a given query vector."""
        if not self._chunks or not query_vector:
            return []

        scored: list[tuple[VectorChunk, float]] = []
        for chunk in self._chunks.values():
            if filter_metadata and not self._matches_filter(chunk.metadata, filter_metadata):
                continue
            sim = cosine_similarity(query_vector, chunk.vector)
            if sim >= min_similarity:
                scored.append((chunk, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        min_similarity: float = -1.0,
    ) -> list[tuple[VectorChunk, float]]:
        """Embed query string and find top-k matching chunks."""
        q_vec = self.embedding_fn(query)
        return self.search_by_vector(
            query_vector=q_vec,
            top_k=top_k,
            filter_metadata=filter_metadata,
            min_similarity=min_similarity,
        )

    @staticmethod
    def _matches_filter(metadata: dict[str, Any], filter_dict: dict[str, Any]) -> bool:
        """Check if metadata matches all filter constraints."""
        for key, val in filter_dict.items():
            meta_val = metadata.get(key)
            if isinstance(val, (list, tuple, set)):
                if isinstance(meta_val, (list, tuple, set)):
                    if not any(item in meta_val for item in val):
                        return False
                elif meta_val not in val:
                    return False
            elif meta_val != val:
                return False
        return True

    def save_to_file(self, path: str | Path) -> None:
        """Serialize index chunks and metadata to a JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "dimension": self.dimension,
            "total_chunks": len(self._chunks),
            "chunks": [chunk.to_dict() for chunk in self._chunks.values()],
        }
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_from_file(self, path: str | Path) -> bool:
        """Load indexed chunks from a serialized JSON file."""
        target = Path(path)
        if not target.exists():
            return False
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            self.dimension = data.get("dimension", self.dimension)
            self._chunks.clear()
            self._doc_to_chunks.clear()
            for chunk_data in data.get("chunks", []):
                chunk = VectorChunk.from_dict(chunk_data)
                self.add_chunk(chunk)
            return True
        except Exception as e:
            logger.warning(f"Failed to load vector index from file: {e}")
            return False

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    @property
    def total_documents(self) -> int:
        return len(self._doc_to_chunks)
