"""
Tests for the MCP cache implementation
"""
import pytest
import asyncio
from fastmcp_openapi.cache import MCPCache, CacheEntry


@pytest.mark.asyncio
async def test_cache_basic_operations():
    """Test basic cache set and get operations"""
    cache = MCPCache(max_size=10, ttl_seconds=60)

    # Create a mock cache entry
    entry = CacheEntry(
        mcp=None,
        name="Test API",
        client=None,
        api_id="test123",
        spec={},
        tools={},
        tools_manager=None
    )

    # Test set and get
    await cache.set("test123", entry)
    retrieved = await cache.get("test123")

    assert retrieved is not None
    assert retrieved.name == "Test API"
    assert retrieved.api_id == "test123"


@pytest.mark.asyncio
async def test_cache_eviction():
    """Test LRU eviction when cache is full"""
    cache = MCPCache(max_size=2, ttl_seconds=60)

    entry1 = CacheEntry(mcp=None, name="API 1", client=None, api_id="id1", spec={}, tools={}, tools_manager=None)
    entry2 = CacheEntry(mcp=None, name="API 2", client=None, api_id="id2", spec={}, tools={}, tools_manager=None)
    entry3 = CacheEntry(mcp=None, name="API 3", client=None, api_id="id3", spec={}, tools={}, tools_manager=None)

    await cache.set("id1", entry1)
    await cache.set("id2", entry2)
    await cache.set("id3", entry3)  # Should evict id1

    assert await cache.get("id1") is None
    assert await cache.get("id2") is not None
    assert await cache.get("id3") is not None


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics tracking"""
    cache = MCPCache(max_size=10, ttl_seconds=60)

    entry = CacheEntry(mcp=None, name="Test", client=None, api_id="test", spec={}, tools={}, tools_manager=None)

    # Generate some hits and misses
    await cache.set("test", entry)
    await cache.get("test")  # Hit
    await cache.get("nonexistent")  # Miss

    stats = cache.stats()

    assert stats['size'] == 1
    assert stats['hits'] >= 1
    assert stats['misses'] >= 1
