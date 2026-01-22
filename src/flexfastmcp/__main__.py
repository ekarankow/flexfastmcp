"""
Main entry point for running the FlexFastMCP OpenAPI Middleware server
"""

if __name__ == "__main__":
    from .server import mcp, _mcp_cache, startup, shutdown, logger
    import asyncio
    import os

    port = int(os.getenv("MCP_PORT", "8080"))

    logger.info("Starting FlexFastMCP")
    logger.info(f"Port: {port}")
    logger.info("Middleware: FlexFastMCP")
    logger.info(f"Cache: max_size={_mcp_cache._max_size}, ttl={_mcp_cache._ttl_seconds}s")
    logger.info("Pass OpenAPI spec in _meta.openapi for dynamic routing")

    asyncio.run(startup())

    try:
        mcp.run(transport="streamable-http", port=port)
    finally:
        asyncio.run(shutdown())
