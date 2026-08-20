"""Tests for PaperCache service (In-Memory LRU and Redis tier)."""

import pytest

from openmlr.services.paper_cache import PaperCache, paper_cache


@pytest.mark.asyncio
class TestPaperCache:
    async def test_singleton_exists(self):
        assert paper_cache is not None
        assert isinstance(paper_cache, PaperCache)

    async def test_in_memory_get_set_search(self):
        cache = PaperCache(in_memory_limit=10, default_ttl=3600)
        await cache.set_cached_search("diffusion models", "Result list 1", {"year_from": 2024})

        res = await cache.get_cached_search("diffusion models", {"year_from": 2024})
        assert res == "Result list 1"

        # Different filter should miss
        miss = await cache.get_cached_search("diffusion models", {"year_from": 2023})
        assert miss is None

    async def test_in_memory_get_set_paper(self):
        cache = PaperCache(in_memory_limit=5, default_ttl=3600)
        await cache.set_cached_paper("2301.12345", {"title": "Test Paper", "year": 2023})

        paper = await cache.get_cached_paper("2301.12345")
        assert paper is not None
        assert paper["title"] == "Test Paper"

    async def test_lru_eviction(self):
        cache = PaperCache(in_memory_limit=2, default_ttl=3600)
        await cache.set_cached_paper("p1", {"title": "P1"})
        await cache.set_cached_paper("p2", {"title": "P2"})
        await cache.set_cached_paper("p3", {"title": "P3"})

        # p1 should be evicted from in-memory tier
        p1 = await cache.get_cached_paper("p1")
        assert p1 is None

        p2 = await cache.get_cached_paper("p2")
        assert p2 is not None

        p3 = await cache.get_cached_paper("p3")
        assert p3 is not None

    async def test_cache_stats_and_clear(self):
        cache = PaperCache(in_memory_limit=10)
        cache.clear()

        await cache.set_cached_paper("p1", "Content 1")
        _ = await cache.get_cached_paper("p1")  # Hit
        _ = await cache.get_cached_paper("p2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5
        assert stats["in_memory_entries"] == 1

        cache.clear()
        stats_cleared = cache.get_stats()
        assert stats_cleared["in_memory_entries"] == 0
        assert stats_cleared["hits"] == 0
