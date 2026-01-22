"""
MCP Cache Manager
Manages cached MCP instances with size limits and TTL
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the MCP cache"""
    mcp: Any
    name: str
    client: Any
    api_id: str
    spec: Dict[str, Any]
    tools: Dict[str, Any]
    tools_manager: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def touch(self):
        """Update last accessed time and increment counter"""
        self.last_accessed = time.time()
        self.access_count += 1

    def is_expired(self, ttl: int) -> bool:
        """Check if entry has expired based on TTL"""
        if ttl <= 0:  # 0 or negative means no expiry
            return False
        return (time.time() - self.last_accessed) > ttl

    def age_seconds(self) -> float:
        """Get age of entry in seconds"""
        return time.time() - self.created_at


class MCPCache:
    """
    Thread-safe cache for MCP instances with LRU eviction and TTL support.

    Features:
    - Maximum size limit with LRU eviction
    - TTL (time-to-live) for cache entries
    - Automatic cleanup of expired entries
    - Access tracking and statistics
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,  # 1 hour default
        cleanup_interval: int = 300  # 5 minutes
    ):
        """
        Initialize MCP cache.

        Args:
            max_size: Maximum number of entries (0 = unlimited)
            ttl_seconds: Time-to-live for entries in seconds (0 = no expiry)
            cleanup_interval: Interval for cleanup task in seconds
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cleanup_interval = cleanup_interval
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'cleanups': 0
        }

        logger.info(f"Initialized MCP cache (max_size={max_size}, ttl={ttl_seconds}s)")

    async def get(self, api_id: str) -> Optional[CacheEntry]:
        """
        Get entry from cache.

        Args:
            api_id: Unique API identifier

        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(api_id)

            if entry is None:
                self._stats['misses'] += 1
                return None

            # Check if expired
            if entry.is_expired(self._ttl_seconds):
                logger.info(f"Cache entry expired: {api_id} (age: {entry.age_seconds():.0f}s)")
                await self._remove_entry(api_id, reason='expired')
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None

            # Update access tracking and move to end (LRU)
            entry.touch()
            self._cache.move_to_end(api_id)
            self._stats['hits'] += 1

            return entry

    async def set(self, api_id: str, entry: CacheEntry) -> None:
        """
        Add or update entry in cache.

        Args:
            api_id: Unique API identifier
            entry: Cache entry to store
        """
        async with self._lock:
            # Check if we need to evict
            if self._max_size > 0 and api_id not in self._cache:
                while len(self._cache) >= self._max_size:
                    await self._evict_lru()

            # Add/update entry
            self._cache[api_id] = entry
            self._cache.move_to_end(api_id)

            logger.info(f"Cached MCP: {entry.name} (ID: {api_id}, size: {len(self._cache)})")

    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._cache:
            return

        # Get oldest entry (first in OrderedDict)
        lru_id = next(iter(self._cache))
        entry = self._cache[lru_id]

        logger.info(f"Evicting LRU entry: {entry.name} (ID: {lru_id}, accesses: {entry.access_count})")
        await self._remove_entry(lru_id, reason='evicted')
        self._stats['evictions'] += 1

    async def _remove_entry(self, api_id: str, reason: str = 'removed') -> None:
        """
        Remove entry from cache and cleanup resources.

        Args:
            api_id: API identifier
            reason: Reason for removal (for logging)
        """
        entry = self._cache.get(api_id)
        if not entry:
            return

        # Close HTTP client if present
        if entry.client:
            try:
                await entry.client.aclose()
                logger.debug(f"Closed HTTP client for {api_id}")
            except Exception as e:
                logger.warning(f"Error closing client for {api_id}: {e}")

        # Remove from cache
        del self._cache[api_id]
        logger.debug(f"Removed cache entry: {api_id} ({reason})")

    async def remove(self, api_id: str) -> bool:
        """
        Manually remove entry from cache.

        Args:
            api_id: API identifier

        Returns:
            True if entry was removed, False if not found
        """
        async with self._lock:
            if api_id in self._cache:
                await self._remove_entry(api_id, reason='manual')
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from cache"""
        async with self._lock:
            logger.info(f"Clearing cache ({len(self._cache)} entries)")

            # Close all clients
            for api_id in list(self._cache.keys()):
                await self._remove_entry(api_id, reason='cleared')

            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        if self._ttl_seconds <= 0:
            return 0

        async with self._lock:
            expired_ids = []

            for api_id, entry in self._cache.items():
                if entry.is_expired(self._ttl_seconds):
                    expired_ids.append(api_id)

            for api_id in expired_ids:
                await self._remove_entry(api_id, reason='expired')
                self._stats['expirations'] += 1

            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired entries")

            self._stats['cleanups'] += 1
            return len(expired_ids)

    def start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info(f"Started cleanup task (interval: {self._cleanup_interval}s)")

    def stop_cleanup_task(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("Stopped cleanup task")

    async def _cleanup_loop(self) -> None:
        """Background task to periodically cleanup expired entries"""
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_expired()
        except asyncio.CancelledError:
            logger.debug("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        hit_rate = 0.0
        total_requests = self._stats['hits'] + self._stats['misses']
        if total_requests > 0:
            hit_rate = (self._stats['hits'] / total_requests) * 100

        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'ttl_seconds': self._ttl_seconds,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': f"{hit_rate:.2f}%",
            'evictions': self._stats['evictions'],
            'expirations': self._stats['expirations'],
            'cleanups': self._stats['cleanups'],
            'entries': [
                {
                    'api_id': api_id,
                    'name': entry.name,
                    'age_seconds': entry.age_seconds(),
                    'access_count': entry.access_count,
                    'tools_count': len(entry.tools)
                }
                for api_id, entry in self._cache.items()
            ]
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.start_cleanup_task()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.stop_cleanup_task()
        await self.clear()
