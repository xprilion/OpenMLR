"""Tests for hybrid search (dense vector + sparse BM25) and knowledge graph retrieval."""

import tempfile
from pathlib import Path

import pytest

from openmlr.services.hybrid_search import (
    BM25Index,
    HybridSearchEngine,
    SearchResult,
    tokenize,
)
from openmlr.services.vector_index import (
    VectorIndex,
    cosine_similarity,
    generate_deterministic_embedding,
)
from openmlr.workspace.knowledge import KnowledgeGraph


class TestVectorIndex:
    """Test dense vector index and embeddings."""

    def test_cosine_similarity(self):
        assert cosine_similarity([], []) == 0.0
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
        assert pytest.approx(cosine_similarity([1.0, 0.0], [1.0, 0.0])) == 1.0
        assert pytest.approx(cosine_similarity([1.0, 2.0], [2.0, 4.0])) == 1.0
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_deterministic_embedding(self):
        vec_empty = generate_deterministic_embedding("")
        assert all(x == 0.0 for x in vec_empty)
        assert len(vec_empty) == 64

        vec1 = generate_deterministic_embedding("attention is all you need")
        assert len(vec1) == 64
        # Unit magnitude check
        norm = sum(x * x for x in vec1) ** 0.5
        assert pytest.approx(norm) == 1.0

        vec2 = generate_deterministic_embedding("attention is all you need")
        assert vec1 == vec2

        vec3 = generate_deterministic_embedding("convolutional neural networks")
        sim_same = cosine_similarity(vec1, vec2)
        sim_diff = cosine_similarity(vec1, vec3)
        assert sim_same > sim_diff

    def test_vector_index_add_search(self):
        idx = VectorIndex(dimension=32)
        idx.add_text_chunk(
            chunk_id="c1",
            doc_id="d1",
            text="Transformer attention mechanism in deep learning",
            metadata={"domain": "nlp"},
        )
        idx.add_text_chunk(
            chunk_id="c2",
            doc_id="d2",
            text="ResNet deep residual learning for image recognition",
            metadata={"domain": "vision"},
        )

        assert idx.total_chunks == 2
        assert idx.total_documents == 2

        results = idx.search("attention mechanism", top_k=2)
        assert len(results) == 2
        assert results[0][0].chunk_id == "c1"

        # Test metadata filtering
        vision_results = idx.search("learning", top_k=2, filter_metadata={"domain": "vision"})
        assert len(vision_results) == 1
        assert vision_results[0][0].chunk_id == "c2"

    def test_vector_index_chunking(self):
        idx = VectorIndex(dimension=16)
        long_text = " ".join([f"word_{i}" for i in range(100)])
        chunks = idx.add_document("doc_long", long_text, chunk_size=30, chunk_overlap=10)
        assert len(chunks) > 1
        assert idx.get_chunk("doc_long#chunk_0") is not None
        assert len(idx.get_document_chunks("doc_long")) == len(chunks)

        deleted = idx.delete_document("doc_long")
        assert deleted == len(chunks)
        assert idx.total_chunks == 0

    def test_vector_index_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_vec.json"
            idx1 = VectorIndex(dimension=16)
            idx1.add_text_chunk("c1", "d1", "Transformer model", metadata={"tag": "ai"})
            idx1.save_to_file(path)

            idx2 = VectorIndex(dimension=16)
            assert idx2.load_from_file(path) is True
            assert idx2.total_chunks == 1
            assert (chunk := idx2.get_chunk("c1")) is not None
            assert chunk.text == "Transformer model"


class TestBM25Index:
    """Test sparse lexical BM25 index."""

    def test_tokenize(self):
        tokens = tokenize("Attention Is ALL You Need! (2017)")
        assert "attention" in tokens
        assert "need" in tokens
        assert "is" not in tokens  # stopword

    def test_bm25_search(self):
        bm25 = BM25Index()
        bm25.add_document(
            "d1", "Deep residual learning for image classification", {"modality": "vision"}
        )
        bm25.add_document(
            "d2", "Attention mechanism and transformers for natural language", {"modality": "nlp"}
        )
        bm25.add_document(
            "d3", "Diffusion models for generative image synthesis", {"modality": "vision"}
        )

        results = bm25.search("transformers natural language", top_k=3)
        assert len(results) >= 1
        assert results[0][0].doc_id == "d2"

        filtered = bm25.search("image", top_k=3, filter_metadata={"modality": "vision"})
        assert all(r[0].metadata["modality"] == "vision" for r in filtered)

        bm25.delete_document("d2")
        assert len(bm25.search("transformers", top_k=3)) == 0


class TestHybridSearchEngine:
    """Test blended sparse + dense hybrid search."""

    def test_hybrid_search_scoring(self):
        engine = HybridSearchEngine(dimension=32)
        engine.index_document(
            "doc1",
            "FlashAttention fast and memory-efficient exact attention with IO-awareness",
            metadata={"category": "optimization"},
        )
        engine.index_document(
            "doc2",
            "LoRA low-rank adaptation of large language models for fine-tuning",
            metadata={"category": "fine-tuning"},
        )

        results_blended = engine.search("flashattention memory IO", top_k=2, alpha=0.5)
        assert len(results_blended) >= 1
        assert results_blended[0].doc_id == "doc1"
        assert isinstance(results_blended[0], SearchResult)

        dict_res = results_blended[0].to_dict()
        assert dict_res["doc_id"] == "doc1"
        assert "score" in dict_res

        # Test RRF fusion
        results_rrf = engine.search("low-rank adaptation", top_k=2, use_rrf=True)
        assert len(results_rrf) >= 1
        assert results_rrf[0].doc_id == "doc2"

    def test_hybrid_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine1 = HybridSearchEngine(workspace_path=tmpdir, dimension=16)
            engine1.index_document(
                "doc_test", "Benchmarking Transformer architectures on TPU", {"target": "tpu"}
            )
            engine1.save_index()

            engine2 = HybridSearchEngine(workspace_path=tmpdir, dimension=16)
            assert engine2.load_index() is True
            results = engine2.search("Transformer TPU", top_k=1)
            assert len(results) == 1
            assert results[0].doc_id == "doc_test"


class TestKnowledgeGraphHybridIntegration:
    """Test knowledge graph integration with hybrid search."""

    def test_knowledge_graph_hybrid_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KnowledgeGraph(tmpdir)
            kg.add_entity(
                entity_id="paper:vaswani2017",
                entity_type="paper",
                label="Attention Is All You Need",
                properties={
                    "abstract": "Dominant sequence transduction models are based on complex recurrent or convolutional neural networks."
                },
            )
            kg.add_entity(
                entity_id="method:flash_attention",
                entity_type="method",
                label="FlashAttention",
                properties={
                    "description": "Fast and memory-efficient exact attention algorithm using GPU SRAM tiling."
                },
            )

            results = kg.hybrid_search("SRAM tiling GPU attention", top_k=2)
            assert len(results) >= 1
            assert results[0]["doc_id"] == "method:flash_attention"
            assert results[0]["entity"]["label"] == "FlashAttention"

            # Filter by entity_type
            paper_results = kg.hybrid_search("attention", top_k=2, entity_type="paper")
            assert len(paper_results) == 1
            assert paper_results[0]["doc_id"] == "paper:vaswani2017"
