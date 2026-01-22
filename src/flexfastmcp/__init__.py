"""
FlexFastMCP OpenAPI Middleware
A transparent proxy server for dynamically routing MCP protocol requests to OpenAPI-based services.
"""

__version__ = "0.1.0"
__author__ = "FastMCP OpenAPI Team"

from .cache import MCPCache, CacheEntry
from .server import FlexFastMCP

__all__ = [
    "MCPCache",
    "CacheEntry",
    "FlexFastMCP",
]
