# Migration Guide

## From Root-Level Scripts to Package Structure

If you were using the old root-level scripts, here's how to migrate:

### Old Way (Deprecated)

```bash
python flexfastmcp_middleware.py
```

### New Way

```bash
# Install the package
pip install -e .

# Run as a module
python -m flexfastmcp

# Or use the scripts
./scripts/run.sh
```

### Import Changes

**Old imports:**
```python
from mcp_cache import MCPCache, CacheEntry
```

**New imports:**
```python
from flexfastmcp import MCPCache, CacheEntry
from flexfastmcp.server import FlexFastMCP
from flexfastmcp.cache import MCPCache
```

### Docker Changes

**Old Dockerfile:**
```dockerfile
COPY flexfastmcp_middleware.py ./
COPY mcp_cache.py ./
CMD ["python", "flexfastmcp_middleware.py"]
```

**New Dockerfile:**
```dockerfile
COPY src/ ./src/
CMD ["python", "-m", "flexfastmcp"]
```

## File Locations

### Before

```
.
├── flexfastmcp_middleware.py
├── mcp_cache.py
├── run_middleware_server.sh
└── test_middleware_server.py
```

### After

```
.
├── src/
│   └── flexfastmcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py (was flexfastmcp_middleware.py)
│       └── cache.py (was mcp_cache.py)
├── scripts/
│   ├── run.sh (replaces run_middleware_server.sh)
│   └── run.bat
├── tests/
│   └── test_cache.py (replaces test_middleware_server.py)
└── examples/
    └── basic_usage.py
```

## Configuration Files

No changes required for:
- `.env` and `.env.example`
- `requirements.txt`
- `docker-compose.yml` (automatically updated)

## Breaking Changes

None - the API and behavior remain the same, only the project structure changed.
