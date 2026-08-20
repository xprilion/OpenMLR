"""Two-tier caching service for academic paper searches and paper metadata.

Tier 1: In-Memory LRU Cache (Fastest, zero-network overhead)
Tier 2: Redis Cache (Shared across workers, persistent across restarts, 24h TTL)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

from .redis_pubsub import get_redis

log = logging.getLogger(__name__)

# Default cache TTL: 24 hours (86,400 seconds)
DEFAULT_CACHE_TTL = 86400
MAX_IN_MEMORY_ENTRIES = 500


class PaperCache:
    """High-throughput multi-tier paper cache."""

    def __init__(
        self, in_memory_limit: int = MAX_IN_MEMORY_ENTRIES, default_ttl: int = DEFAULT_CACHE_TTL
    ):
        self.in_memory_limit = in_memory_limit
        self.default_ttl = default_ttl
        self._lru_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _normalize_key(self, prefix: str, identifier: str) -> str:
        clean_id = identifier.strip().lower()
        key_hash = hashlib.sha256(clean_id.encode("utf-8")).hexdigest()[:16]
        return f"openmlr:paper_cache:{prefix}:{key_hash}"

    def _make_search_key(self, query: str, filters: dict | None = None) -> str:
        filter_str = json.dumps(filters or {}, sort_keys=True)
        combined = f"query:{query.strip().lower()}|filters:{filter_str}"
        return self._normalize_key("search", combined)

    def _make_paper_key(self, paper_id: str) -> str:
        return self._normalize_key("paper", paper_id)

    async def get_cached_search(self, query: str, filters: dict | None = None) -> Any | None:
        """Retrieve cached search results from In-Memory or Redis."""
        key = self._make_search_key(query, filters)
        return await self._get(key)

    async def set_cached_search(
        self,
        query: str,
        results: Any,
        filters: dict | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store search results in both In-Memory and Redis tiers."""
        key = self._make_search_key(query, filters)
        await self._set(key, results, ttl_seconds or self.default_ttl)

    async def get_cached_paper(self, paper_id: str) -> Any | None:
        """Retrieve cached paper metadata."""
        key = self._make_paper_key(paper_id)
        return await self._get(key)

    async def set_cached_paper(
        self,
        paper_id: str,
        data: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store paper metadata in both In-Memory and Redis tiers."""
        key = self._make_paper_key(paper_id)
        await self._set(key, data, ttl_seconds or self.default_ttl)

    async def _get(self, key: str) -> Any | None:
        now = time.time()

        # 1. Check In-Memory LRU Cache
        if key in self._lru_cache:
            expires_at, val = self._lru_cache[key]
            if now < expires_at:
                self._lru_cache.move_to_end(key)
                self._hits += 1
                return val
            # Expired in-memory entry
            del self._lru_cache[key]

        # 2. Check Redis Cache
        try:
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                val = json.loads(raw)
                # Populate back into in-memory LRU
                self._put_in_memory(key, val, now + 3600)  # 1hr memory cache
                self._hits += 1
                return val
        except Exception as exc:
            log.debug("Redis cache get error: %s", exc)

        self._misses += 1
        return None

    async def _set(self, key: str, value: Any, ttl_seconds: int) -> None:
        now = time.time()
        expires_at = now + ttl_seconds

        # 1. Set in In-Memory LRU
        self._put_in_memory(key, value, expires_at)

        # 2. Set in Redis
        try:
            redis = await get_redis()
            payload = json.dumps(value)
            await redis.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            log.debug("Redis cache set error: %s", exc)

    def _put_in_memory(self, key: str, value: Any, expires_at: float) -> None:
        if key in self._lru_cache:
            del self._lru_cache[key]
        elif len(self._lru_cache) >= self.in_memory_limit:
            self._lru_cache.popitem(last=False)
        self._lru_cache[key] = (expires_at, value)

    def clear(self) -> None:
        """Clear the in-memory cache."""
        self._lru_cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance metrics."""
        total = self._hits + self._misses
        hit_ratio = round((self._hits / total) if total > 0 else 0.0, 4)
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": hit_ratio,
            "in_memory_entries": len(self._lru_cache),
            "in_memory_capacity": self.in_memory_limit,
        }


# Global singleton instance
paper_cache = PaperCache()
