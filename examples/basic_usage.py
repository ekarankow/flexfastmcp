#!/usr/bin/env python3
"""
Basic usage example for fastmcp-openapi
Demonstrates how to use the middleware server with a simple OpenAPI spec
"""

import asyncio
import httpx
import json

# Sample TODO API OpenAPI spec
TODO_API_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "JSONPlaceholder TODO API",
        "version": "1.0.0"
    },
    "servers": [
        {"url": "https://jsonplaceholder.typicode.com"}
    ],
    "paths": {
        "/todos": {
            "get": {
                "operationId": "listTodos",
                "summary": "List all todos",
                "responses": {
                    "200": {
                        "description": "Success"
                    }
                }
            }
        }
    }
}


async def main():
    """Demo the middleware server"""
    base_url = "http://localhost:3000"

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        print("📋 FlexFastMCP OpenAPI Middleware - Basic Usage Example\n")

        # 1. Check proxy status
        print("1. Checking proxy status...")
        response = await client.post('/messages', json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "proxy_status",
                "arguments": {}
            }
        })
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Proxy is running")
            print(f"   Cache size: {json.loads(result['result']['content'][0]['text'])['cache']['size']}\n")

        # 2. List tools from OpenAPI spec
        print("2. Listing tools from TODO API...")
        response = await client.post('/messages', json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {
                "_meta": {
                    "openapi": TODO_API_SPEC
                }
            }
        })
        if response.status_code == 200:
            result = response.json()
            tools = result.get('result', {}).get('tools', [])
            print(f"   ✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"      - {tool['name']}: {tool.get('description', 'No description')}")
            print()

        # 3. Call a tool
        print("3. Calling listTodos tool...")
        response = await client.post('/messages', json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "listTodos",
                "arguments": {},
                "_meta": {
                    "openapi": TODO_API_SPEC
                }
            }
        })
        if response.status_code == 200:
            result = response.json()
            content = result['result']['content'][0]['text']
            todos = json.loads(content)
            print(f"   ✅ Retrieved {len(todos)} todos")
            print(f"   First todo: {todos[0]['title']}\n")

        print("✨ Example completed successfully!")


if __name__ == "__main__":
    print("Make sure the server is running: python -m fastmcp_openapi\n")
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print("❌ Could not connect to server at localhost:3000")
        print("   Start it with: python -m fastmcp_openapi")
