#!/usr/bin/env python3
"""
FlexFastMCP Server with OpenAPI Middleware
Dynamically routes MCP protocol requests based on OpenAPI specs in _meta.openapi
"""

import json
import httpx
import hashlib
import logging
import asyncio
import os
import atexit
from typing import Sequence, Dict, Any, Optional
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult
from starlette.requests import Request

from src.flexfastmcp import MCPCache, CacheEntry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_mcp_cache = MCPCache(
    max_size=int(os.getenv('MCP_CACHE_MAX_SIZE', '100')),
    ttl_seconds=int(os.getenv('MCP_CACHE_TTL', '3600')),
    cleanup_interval=int(os.getenv('MCP_CACHE_CLEANUP_INTERVAL', '300'))
)

def get_api_id(spec: Dict[str, Any]) -> str:
    """Generate unique ID for an OpenAPI spec"""
    return hashlib.md5(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]

async def _extract_spec_from_request(request: Request) -> Optional[str]:
    """
    Extract OpenAPI spec from X-META header or MCP metadata.
    Priority: X-META header > _meta.openapi in request body
    Returns: OpenAPI spec as JSON string or None
    """
    for header_name, header_value in request.headers.items():
        if header_name.lower() == "x-meta":
            logger.debug("Found OpenAPI spec in X-META header")
            return header_value

    try:
        request_body = await request.json()
        params = request_body.get("params", {})
        if "_meta" in params and isinstance(params["_meta"], dict):
            meta = params["_meta"]
            if "openapi" in meta:
                spec = meta["openapi"]
                logger.debug("Found OpenAPI spec in MCP _meta.openapi")

                if isinstance(spec, dict):
                    return json.dumps(spec)
                elif isinstance(spec, str):
                    spec_stripped = spec.strip()
                    if spec_stripped.startswith('{'):
                        return spec
                    else:
                        try:
                            import yaml
                            spec_dict = yaml.safe_load(spec)
                            return json.dumps(spec_dict)
                        except ImportError:
                            logger.warning("YAML support not available, install pyyaml: pip install pyyaml")
                            return spec
                        except Exception as yaml_error:
                            logger.warning(f"Failed to parse as YAML: {yaml_error}, trying as JSON")
                            return spec
    except Exception as e:
        logger.debug(f"Could not extract spec from request body: {e}")

    return None

def _base_url_from_spec(openapi_spec: Dict[str, Any]) -> Optional[str]:
    servers = openapi_spec.get("servers")
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict) and first.get("url"):
            return first["url"]
        if isinstance(first, str):
            return first

    if openapi_spec.get("swagger") == "2.0" or "swagger" in openapi_spec:
        host = openapi_spec.get("host")
        if host:
            schemes = openapi_spec.get("schemes") or []
            scheme = schemes[0] if schemes else "https"
            base_path = openapi_spec.get("basePath", "")
            if base_path and not base_path.startswith("/"):
                base_path = f"/{base_path}"
            return f"{scheme}://{host}{base_path}"

    if openapi_spec.get("x-base-url"):
        return openapi_spec["x-base-url"]

    return None

async def get_or_create_mcp(spec_json: str, request: Request) -> Optional[CacheEntry]:
    """Get or create MCP instance for an OpenAPI spec (supports JSON and YAML)"""
    try:
        openapi_spec = json.loads(spec_json)
        logger.debug("Parsed OpenAPI spec as JSON")
    except json.JSONDecodeError:
        try:
            import yaml
            openapi_spec = yaml.safe_load(spec_json)
            logger.debug("Parsed OpenAPI spec as YAML")
        except ImportError:
            logger.error("YAML parsing failed: pyyaml not installed. Install with: pip install pyyaml")
            return None
        except Exception as yaml_error:
            logger.error(f"Failed to parse OpenAPI spec: {yaml_error}")
            return None

    api_id = get_api_id(openapi_spec)
    cache_entry = await _mcp_cache.get(api_id)
    if cache_entry:
        return cache_entry

    try:
        meta = {}
        try:
            request_body = await request.json()
            params = request_body.get('params', {})
            meta = params.get('_meta') or params.get('meta', {})
        except:
            pass

        header_base_url = request.headers.get("x-base-url")
        if header_base_url:
            logger.info(f"Using base URL from X-BASE-URL header: {header_base_url}")

        base_url = header_base_url or meta.get("base_url") or meta.get("baseurl") or meta.get("baseURL")
        if not base_url:
            base_url = _base_url_from_spec(openapi_spec)

        if base_url:
            if "servers" not in openapi_spec:
                openapi_spec["servers"] = []
            if openapi_spec["servers"]:
                if isinstance(openapi_spec["servers"][0], dict):
                    openapi_spec["servers"][0]["url"] = base_url
                else:
                    openapi_spec["servers"][0] = {"url": base_url}
            else:
                openapi_spec["servers"].append({"url": base_url})
        headers = {}
        if meta.get('auth_token'):
            headers["Authorization"] = f"Bearer {meta['auth_token']}"
        if meta.get('api_key'):
            headers["X-API-Key"] = meta['api_key']

        if base_url:
            client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30.0)
        else:
            logger.info("No base URL provided; relying on OpenAPI servers or absolute URLs")
            client = httpx.AsyncClient(headers=headers, timeout=30.0)
        api_name = openapi_spec.get('info', {}).get('title', 'Unknown API')
        mcp_instance = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=client,
            name=api_name
        )

        tools_manager = getattr(mcp_instance, '_tool_manager', None)
        tools_dict = getattr(tools_manager, '_tools', None) or getattr(mcp_instance, 'tools', {})

        entry = CacheEntry(
            mcp=mcp_instance,
            name=api_name,
            client=client,
            api_id=api_id,
            spec=openapi_spec,
            tools=tools_dict,
            tools_manager=tools_manager
        )

        await _mcp_cache.set(api_id, entry)
        logger.info(f"Created MCP for: {api_name} (ID: {api_id}, {len(tools_dict)} tools)")
        return entry

    except Exception as e:
        logger.error(f"Error creating MCP: {e}", exc_info=True)
        return None

class FlexFastMCP(Middleware):
    """Middleware to intercept and handle all MCP protocol requests."""

    async def on_list_resources(self, context: MiddlewareContext, call_next):
        """Intercept list_resources"""
        logger.debug("Intercepting list_resources")
        try:
            request = get_http_request()
            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                return []

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                return []

            resources = getattr(cache_entry.mcp, '_resources', [])
            logger.info(f"Returning {len(resources)} resources")
            return resources
        except Exception as e:
            logger.error(f"Error in list_resources: {e}", exc_info=True)
            return []

    async def on_read_resource(self, context: MiddlewareContext, call_next):
        """Intercept read_resource"""
        logger.debug("Intercepting read_resource")
        resource_uri = None
        try:
            request = get_http_request()
            request_body = await request.json()
            params = request_body.get("params", {})
            resource_uri = params.get("uri")
            logger.info(f"Read resource: {resource_uri}")

            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                return {"contents": [{"uri": resource_uri, "mimeType": "text/plain", "text": "Error: No OpenAPI spec"}]}

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                return {"contents": [{"uri": resource_uri, "mimeType": "text/plain", "text": "Error: Failed to create MCP"}]}

            if hasattr(cache_entry.mcp, '_resource_manager'):
                return await cache_entry.mcp._resource_manager.read_resource(resource_uri)

            return {"contents": [{"uri": resource_uri, "mimeType": "application/json", "text": spec_json}]}

        except Exception as e:
            logger.error(f"Error in read_resource: {e}", exc_info=True)
            return {"contents": [{"uri": resource_uri, "mimeType": "text/plain", "text": f"Error: {str(e)}"}]}

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        """Intercept list_prompts"""
        logger.debug("Intercepting list_prompts")
        try:
            request = get_http_request()
            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                return []

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                return []

            prompts = getattr(cache_entry.mcp, '_prompts', [])
            logger.info(f"Returning {len(prompts)} prompts")
            return prompts
        except Exception as e:
            logger.error(f"Error in list_prompts: {e}", exc_info=True)
            return []

    async def on_get_prompt(self, context: MiddlewareContext, call_next):
        """Intercept get_prompt"""
        logger.debug("Intercepting get_prompt")
        try:
            request = get_http_request()
            request_body = await request.json()
            params = request_body.get("params", {})
            prompt_name = params.get("name")
            prompt_arguments = params.get("arguments", {})
            logger.info(f"Get prompt: {prompt_name}")

            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                return {"description": "Error", "messages": [{"role": "user", "content": {"type": "text", "text": "Error: No OpenAPI spec"}}]}

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                return {"description": "Error", "messages": [{"role": "user", "content": {"type": "text", "text": "Error: Failed to create MCP"}}]}

            if hasattr(cache_entry.mcp, '_prompt_manager'):
                return await cache_entry.mcp._prompt_manager.get_prompt(prompt_name, prompt_arguments)

            api_title = cache_entry.spec.get('info', {}).get('title', 'this API')
            return {
                "description": f"Prompt for {api_title}",
                "messages": [{"role": "user", "content": {"type": "text", "text": f"No prompts available for {api_title}"}}]
            }
        except Exception as e:
            logger.error(f"Error in get_prompt: {e}", exc_info=True)
            return {"description": "Error", "messages": [{"role": "user", "content": {"type": "text", "text": f"Error: {str(e)}"}}]}

    async def on_complete(self, context: MiddlewareContext, call_next):
        """Intercept completion requests"""
        logger.debug("Intercepting complete")
        try:
            request = get_http_request()
            request_body = await request.json()
            params = request_body.get("params", {})
            ref = params.get("ref", {})
            argument = params.get("argument", {})
            logger.info(f"Complete: ref={ref}, argument={argument}")

            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                return {"completion": {"values": []}}

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                return {"completion": {"values": []}}

            if ref.get("type") == "ref/tool" or argument.get("name") == "tool":
                prefix = argument.get("value", "")
                completions = [
                    {"value": name, "description": f"Call {name}", "label": name}
                    for name in cache_entry.tools.keys()
                    if name.lower().startswith(prefix.lower())
                ]
                return {"completion": {"values": completions[:20]}}

            if hasattr(cache_entry.mcp, '_completion_handler'):
                return await cache_entry.mcp._completion_handler(ref, argument)

            return {"completion": {"values": []}}
        except Exception as e:
            logger.error(f"Error in complete: {e}", exc_info=True)
            return {"completion": {"values": []}}

    async def on_list_tools(self, context: MiddlewareContext, call_next) -> Sequence[Tool]:
        """Intercept list_tools to return tools from the OpenAPI-based MCP"""
        logger.debug("Intercepting list_tools")

        try:
            request = get_http_request()
            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                logger.warning("Missing OpenAPI spec in list_tools request")
                return []

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                logger.error("Failed to create MCP from OpenAPI spec")
                return []

            tool_list = []
            for tool_name, tool_def in cache_entry.tools.items():
                if isinstance(tool_def, Tool):
                    tool_list.append(tool_def)
                else:
                    tool = Tool(
                        name=tool_name,
                        description=getattr(tool_def, '__doc__', '') or getattr(tool_def, 'description', f"Operation: {tool_name}"),
                        parameters=getattr(tool_def, '_schema', None) or getattr(tool_def, 'parameters', {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": True
                        })
                    )
                    tool_list.append(tool)

            logger.info(f"Returning {len(tool_list)} tools from {cache_entry.name}")
            return tool_list

        except Exception as e:
            logger.error(f"Error in list_tools: {e}", exc_info=True)
            return []

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Intercept call_tool and route to the OpenAPI-based MCP"""
        logger.debug("Intercepting call_tool")

        try:
            request = get_http_request()
            request_body = await request.json()
            params = request_body.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"Tool call: {tool_name}")
            logger.debug(f"Arguments: {json.dumps(arguments, indent=2)}")

            spec_json = await _extract_spec_from_request(request)
            if not spec_json:
                return ToolResult(
                    content="Missing OpenAPI spec. Provide via X-META header or _meta.openapi",
                    structured_content={"success": False, "error": "Missing OpenAPI spec"}
                )

            cache_entry = await get_or_create_mcp(spec_json, request)
            if not cache_entry:
                return ToolResult(
                    content="Failed to create MCP from OpenAPI spec",
                    structured_content={"success": False, "error": "Failed to create MCP"}
                )

            if tool_name not in cache_entry.tools:
                available = list(cache_entry.tools.keys())
                return ToolResult(
                    content=f"Tool '{tool_name}' not found. Available: {', '.join(available[:5])}",
                    structured_content={"success": False, "error": f"Tool not found", "available_tools": available[:10]}
                )

            logger.info(f"Executing '{tool_name}' from {cache_entry.name}")

            if cache_entry.tools_manager:
                result = await cache_entry.tools_manager.call_tool(tool_name, arguments)
            else:
                tool_func = cache_entry.tools[tool_name]
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(**arguments)
                else:
                    result = tool_func(**arguments)

            if isinstance(result, ToolResult):
                return result

            return ToolResult(
                content=json.dumps(result) if isinstance(result, (dict, list)) else str(result),
                structured_content=result if isinstance(result, dict) else {"result": result}
            )

        except Exception as e:
            logger.error(f"Error in call_tool: {e}", exc_info=True)
            raise e

mcp = FastMCP(name="FlexFastMCP")
mcp.add_middleware(FlexFastMCP())

@mcp.tool()
async def proxy_status() -> Dict[str, Any]:
    """Get proxy status including cache statistics"""
    return {
        "type": "fastmcp_openapi_middleware",
        "description": "Transparent proxy using FlexFastMCP middleware",
        "cache": _mcp_cache.stats()
    }

@mcp.tool()
async def clear_cache() -> Dict[str, Any]:
    """Clear all cached MCP instances"""
    size_before = _mcp_cache.size()
    await _mcp_cache.clear()
    return {"success": True, "message": f"Cleared {size_before} cached MCP instances"}

@mcp.tool()
async def remove_cached_api(api_id: str) -> Dict[str, Any]:
    """Remove a specific API from cache by ID"""
    removed = await _mcp_cache.remove(api_id)
    return {
        "success": removed,
        "message": f"Removed API {api_id} from cache" if removed else f"API {api_id} not found",
        "error": None if removed else f"API {api_id} not found in cache"
    }

async def startup():
    """Start the cache cleanup task"""
    _mcp_cache.start_cleanup_task()
    logger.info("Cache cleanup task started")

async def shutdown():
    """Stop cleanup task and clear cache"""
    _mcp_cache.stop_cleanup_task()
    await _mcp_cache.clear()
    logger.info("Cache cleared and cleanup task stopped")

def cleanup():
    """Sync cleanup wrapper for atexit"""
    try:
        asyncio.run(shutdown())
    except:
        pass

atexit.register(cleanup)

if __name__ == "__main__":
    import os
    port = int(os.getenv("MCP_PORT", "3000"))

    logger.info("Starting FlexFastMCP")
    logger.info(f"Port: {port}")
    logger.info("Middleware: FlexFastMCP")
    logger.info(f"Cache: max_size={_mcp_cache._max_size}, ttl={_mcp_cache._ttl_seconds}s")
    logger.info("Pass OpenAPI spec in _meta.openapi for dynamic routing")

    # Start the cache cleanup task
    asyncio.run(startup())

    # Run with streamable-http transport for full MCP protocol support
    try:
        mcp.run(transport="streamable-http", port=port)
    finally:
        # Cleanup on exit
        asyncio.run(shutdown())