# FlexFastMCP OpenAPI Middleware

A transparent proxy server that dynamically routes MCP (Model Context Protocol) requests to OpenAPI-based services. Built with FastMCP, it provides seamless integration between MCP clients and any OpenAPI-compliant API.

## Features

✨ **Dynamic Routing** - Routes MCP protocol requests based on OpenAPI specs in request metadata
🔄 **Smart Caching** - LRU cache with TTL for MCP instances and HTTP clients
📝 **Full MCP Protocol Support** - Tools, resources, prompts, and completion
🌐 **OpenAPI 3.x Support** - Works with any valid OpenAPI specification (JSON/YAML)
🔒 **Authentication** - Bearer tokens and API keys support
🐳 **Docker Ready** - Production-ready Docker and docker-compose setup
⚡ **High Performance** - Async-first design with connection pooling

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/flexfastmcp.git
cd flexfastmcp

# Install in development mode
pip install -e .

# Or install with optional dependencies
pip install -e ".[dev,performance]"
```

### Running the Server

```bash
# Using Python
python -m flexfastmcp

# Using the run script (Unix)
./scripts/run.sh

# Using the run script (Windows)
scripts\run.bat

# Using Docker
docker-compose up
```

### Basic Usage

```python
import httpx
import asyncio

async def call_api():
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "My API", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users"
                }
            }
        }
    }

    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # List available tools
        response = await client.post('/messages', json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {
                "_meta": {"openapi": openapi_spec}
            }
        })

        # Call a tool
        response = await client.post('/messages', json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "listUsers",
                "arguments": {},
                "_meta": {"openapi": openapi_spec}
            }
        })

asyncio.run(call_api())
```

### Extended OpenAPI Overrides (Optional)

You can optionally extend your OpenAPI operation definitions with `x-mcp` to
customize tool names, tool descriptions, and per-parameter descriptions. If
`x-mcp` is not present, the default FastMCP behavior is used.

```json
{
  "paths": {
    "/users": {
      "get": {
        "operationId": "list_users",
        "summary": "List users",
        "parameters": [
          { "name": "limit", "in": "query", "schema": { "type": "integer" } }
        ],
        "x-mcp": {
          "name": "user_list",
          "description": "List users with pagination and filters",
          "parameters": {
            "limit": { "description": "Max users to return (1-100)" }
          }
        }
      }
    }
  }
}
```

You can also generate an extended spec automatically using the built-in tool:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "generate_extended_openapi",
    "arguments": {
      "spec_path": "C:\\projects\\research\\mcp\\flexfastmcp\\openapi.json",
      "overwrite": false,
      "as_json": true
    }
  }
}
```

## Configuration

Environment variables:

```env
# Server Configuration
MCP_PORT=8080

# Cache Configuration
MCP_CACHE_MAX_SIZE=100
MCP_CACHE_TTL=3600
MCP_CACHE_CLEANUP_INTERVAL=300
```

Base URL selection:

- `X-BASE-URL` header (highest priority)
- `_meta.base_url` / `_meta.baseurl` in request params
- OpenAPI `servers` (or Swagger `host` + `basePath` + `schemes`)

### Using `X-BASE-URL`

```bash
curl -X POST http://localhost:8080/messages \
  -H "Content-Type: application/json" \
  -H "X-BASE-URL: https://api.example.com" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {
      "_meta": {"openapi": {"openapi": "3.0.0", "info": {"title": "My API", "version": "1.0.0"}, "paths": {}}}
    }
  }'
```

### Using `_meta.base_url`

```bash
curl -X POST http://localhost:8080/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {
      "_meta": {
        "base_url": "https://api.example.com",
        "openapi": {"openapi": "3.0.0", "info": {"title": "My API", "version": "1.0.0"}, "paths": {}}
      }
    }
  }'
```

## Project Structure

```
flexfastmcp/
├── src/
│   └── flexfastmcp/
│       ├── __init__.py       # Package exports
│       ├── __main__.py       # Entry point
│       ├── server.py         # Main middleware server
│       └── cache.py          # Cache implementation
├── tests/
│   ├── __init__.py
│   └── test_cache.py         # Cache tests
├── examples/
│   └── basic_usage.py        # Usage examples
├── scripts/
│   ├── run.sh                # Unix run script
│   └── run.bat               # Windows run script
├── docs/
│   └── MCP_CACHE_GUIDE.md    # Cache documentation
├── pyproject.toml            # Project configuration
├── requirements.txt          # Dependencies
├── Dockerfile                # Docker image
├── docker-compose.yml        # Docker composition
└── README.md                 # This file
```

## How It Works

1. **Client Request** - MCP client sends request with OpenAPI spec in `_meta.openapi`
2. **Spec Extraction** - Middleware extracts spec from request headers or body
3. **MCP Creation** - Creates/retrieves cached MCP instance from OpenAPI spec
4. **Request Routing** - Routes request to appropriate tool in the MCP instance
5. **Response Return** - Returns formatted MCP response to client

## Cache Management

The middleware includes built-in cache management tools:

```python
# Check cache status
proxy_status()

# Clear entire cache
clear_cache()

# Remove specific API
remove_cached_api(api_id="abc123")
```

See [MCP_CACHE_GUIDE.md](docs/MCP_CACHE_GUIDE.md) for detailed cache documentation.

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Docker

```bash
# Build image
docker build -t flexfastmcp .

# Run container
docker run -p 8080:8080 -e MCP_CACHE_MAX_SIZE=200 flexfastmcp

# Using docker-compose
docker-compose up

# With sample API
docker-compose --profile with-sample-api up
```

## Examples

See the `examples/` directory for more usage examples:

- `basic_usage.py` - Basic middleware usage
- See individual API examples in repository

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Links

- [FastMCP Documentation](https://gofastmcp.com)
- [OpenAPI Specification](https://swagger.io/specification/)
- [MCP Protocol](https://modelcontextprotocol.io/)
