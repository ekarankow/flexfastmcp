# MCP Cache Manager Guide

A recyclable cache implementation for managing MCP instances with automatic cleanup, size limits, and TTL support.

## 🎯 Features

### 1. **LRU Eviction**
- Automatically removes least recently used entries when cache is full
- Tracks access count and last access time for each entry

### 2. **Time-to-Live (TTL)**
- Entries expire after a configurable TTL period
- Automatic cleanup of expired entries
- Based on last access time (not creation time)

### 3. **Size Limits**
- Maximum cache size enforcement
- Configurable via environment variable
- 0 = unlimited size

### 4. **Background Cleanup**
- Periodic cleanup task removes expired entries
- Configurable cleanup interval
- Runs in background without blocking

### 5. **Statistics Tracking**
- Hit/miss rates
- Eviction counts
- Expiration counts
- Per-entry access tracking

## 📊 Cache Entry Structure

```python
@dataclass
class CacheEntry:
    mcp: Any                    # FastMCP instance
    name: str                   # API name
    client: Any                 # HTTP client
    api_id: str                 # Unique identifier
    spec: Dict[str, Any]        # OpenAPI spec
    tools: Dict[str, Any]       # Tools dict
    tools_manager: Any          # Tools manager
    created_at: float           # Creation timestamp
    last_accessed: float        # Last access timestamp
    access_count: int           # Number of accesses
```

## 🔧 Configuration

### Environment Variables

```env
# Maximum cached MCP instances (0 = unlimited)
MCP_CACHE_MAX_SIZE=100

# TTL in seconds (0 = no expiry)
MCP_CACHE_TTL=3600

# Cleanup interval in seconds
MCP_CACHE_CLEANUP_INTERVAL=300
```

### Programmatic Configuration

```python
cache = MCPCache(
    max_size=100,           # Max 100 entries
    ttl_seconds=3600,       # 1 hour TTL
    cleanup_interval=300    # 5 minute cleanup
)
```

## 🔄 Cache Lifecycle

### 1. **Entry Creation**
```python
entry = CacheEntry(
    mcp=mcp_instance,
    name=api_name,
    client=client,
    api_id=api_id,
    spec=openapi_spec,
    tools=tools_dict,
    tools_manager=tools_manager
)

await cache.set(api_id, entry)
```

### 2. **Entry Access**
```python
entry = await cache.get(api_id)
if entry:
    # Entry found and not expired
    # Automatically touched (updates last_accessed)
```

### 3. **Entry Eviction**
Entries are removed when:
- Cache is full (LRU eviction)
- Entry expires (TTL exceeded)
- Manual removal requested
- Cache is cleared

### 4. **Cleanup**
```python
# Automatic background cleanup
cache.start_cleanup_task()

# Manual cleanup
removed = await cache.cleanup_expired()
```

## 📈 Statistics

```python
stats = cache.stats()

{
    'size': 15,                # Current entries
    'max_size': 100,           # Maximum capacity
    'ttl_seconds': 3600,       # TTL setting
    'hits': 245,               # Cache hits
    'misses': 23,              # Cache misses
    'hit_rate': '91.42%',      # Hit rate percentage
    'evictions': 5,            # LRU evictions
    'expirations': 8,          # TTL expirations
    'cleanups': 12,            # Cleanup runs
    'entries': [               # All cached entries
        {
            'api_id': 'abc123',
            'name': 'TODO API',
            'age_seconds': 1234,
            'access_count': 45,
            'tools_count': 6
        }
    ]
}
```

## 🛠️ Management Tools

The middleware server provides tools to manage the cache:

### 1. **proxy_status**
Get cache statistics:
```json
{
    "name": "proxy_status",
    "arguments": {}
}
```

### 2. **clear_cache**
Clear all cached entries:
```json
{
    "name": "clear_cache",
    "arguments": {}
}
```

### 3. **remove_cached_api**
Remove specific API from cache:
```json
{
    "name": "remove_cached_api",
    "arguments": {
        "api_id": "abc123def456"
    }
}
```

## 💡 Benefits

### 1. **Memory Management**
- Prevents unlimited memory growth
- Automatic cleanup of unused entries
- LRU ensures most useful entries stay cached

### 2. **Performance**
- Reuses MCP instances for frequently accessed APIs
- Avoids repeated OpenAPI parsing
- Connection pooling via cached HTTP clients

### 3. **Resource Cleanup**
- Properly closes HTTP clients
- Prevents resource leaks
- Graceful shutdown handling

### 4. **Observability**
- Detailed statistics
- Per-entry metrics
- Access tracking

## 🔍 How Eviction Works

### LRU (Least Recently Used)
```
Cache Full: [API-A(10 acc), API-B(5 acc), API-C(2 acc)]
New API-D arrives
→ Evicts API-C (least recently used)
Cache Now: [API-A, API-B, API-D]
```

### TTL (Time-to-Live)
```
Entry created: t=0
TTL: 3600s (1 hour)
Last access: t=3000s
Current time: t=7000s
→ Age from last access: 4000s > 3600s
→ Entry expired, removed on next access/cleanup
```

## 🚦 Production Recommendations

### Small Deployments
```env
MCP_CACHE_MAX_SIZE=50
MCP_CACHE_TTL=1800        # 30 minutes
MCP_CACHE_CLEANUP_INTERVAL=300
```

### Medium Deployments
```env
MCP_CACHE_MAX_SIZE=200
MCP_CACHE_TTL=3600        # 1 hour
MCP_CACHE_CLEANUP_INTERVAL=600
```

### Large Deployments
```env
MCP_CACHE_MAX_SIZE=1000
MCP_CACHE_TTL=7200        # 2 hours
MCP_CACHE_CLEANUP_INTERVAL=900
```

### High-Traffic APIs
```env
MCP_CACHE_MAX_SIZE=0      # Unlimited (use with caution)
MCP_CACHE_TTL=0           # No expiry
MCP_CACHE_CLEANUP_INTERVAL=0  # No cleanup needed
```

## 🔐 Thread Safety

The cache is thread-safe through:
- Async lock (`asyncio.Lock`)
- Atomic operations
- Proper async/await usage

## 📊 Monitoring

Monitor cache health via:
- Hit rate (aim for >80%)
- Eviction rate (high = cache too small)
- Expiration rate (high = TTL too short)

## 🎉 Summary

The `MCPCache` class provides production-ready cache management with:
- Automatic resource cleanup
- Memory limits
- Time-based expiration
- LRU eviction
- Background cleanup
- Detailed statistics

Perfect for managing dynamic MCP instances in the transparent proxy!