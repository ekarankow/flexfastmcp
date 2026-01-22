# Setup Guide

Complete guide to setting up FlexFastMCP OpenAPI Middleware.

## Prerequisites

- Python 3.9 or higher
- pip or poetry
- (Optional) Docker and docker-compose

## Installation Methods

### Method 1: Development Installation

For development and testing:

```bash
# Clone the repository
git clone https://github.com/yourusername/fastmcp-openapi.git
cd fastmcp-openapi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Method 2: Production Installation

From PyPI (when published):

```bash
pip install fastmcp-openapi

# With optional performance improvements
pip install fastmcp-openapi[performance]
```

### Method 3: Docker

```bash
# Pull and run
docker pull ghcr.io/yourusername/fastmcp-openapi:latest
docker run -p 3000:3000 ghcr.io/yourusername/fastmcp-openapi

# Or build locally
docker build -t fastmcp-openapi .
docker run -p 3000:3000 fastmcp-openapi
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Server
MCP_PORT=3000

# Cache
MCP_CACHE_MAX_SIZE=100
MCP_CACHE_TTL=3600
MCP_CACHE_CLEANUP_INTERVAL=300

```

### Docker Compose

Use the provided `docker-compose.yml`:

```bash
# Start the server
docker-compose up

# With sample API
docker-compose --profile with-sample-api up

# In background
docker-compose up -d
```

## Running the Server

### Quick Start

```bash
# Using module
python -m fastmcp_openapi

# Using script (Unix)
./scripts/run.sh

# Using script (Windows)
scripts\run.bat
```

### With Custom Port

```bash
MCP_PORT=8080 python -m fastmcp_openapi
```

### With Custom Configuration

```bash
MCP_CACHE_MAX_SIZE=200 MCP_CACHE_TTL=7200 python -m fastmcp_openapi
```

## Verification

### Check Server Status

```bash
curl -X POST http://localhost:3000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "proxy_status",
      "arguments": {}
    }
  }'
```

### Run Examples

```bash
# Make sure server is running first
python examples/basic_usage.py
```

### Run Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=fastmcp_openapi --cov-report=html

# Run specific test
pytest tests/test_cache.py -v
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 3000
lsof -i :3000  # Unix
netstat -ano | findstr :3000  # Windows

# Use a different port
MCP_PORT=3001 python -m fastmcp_openapi
```

### Import Errors

```bash
# Reinstall in editable mode
pip install -e .

# Or check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Docker Issues

```bash
# Rebuild without cache
docker-compose build --no-cache

# Check logs
docker-compose logs -f

# Reset everything
docker-compose down -v
docker system prune -af
```

## Next Steps

- Read the [README.md](../README.md) for usage examples
- Check [MCP_CACHE_GUIDE.md](MCP_CACHE_GUIDE.md) for cache configuration
- See [MIGRATION.md](MIGRATION.md) if upgrading from old structure
- Review [examples/](../examples/) for more usage patterns
