#!/bin/bash
# Run the FlexFastMCP OpenAPI Middleware Server

set -e

cd "$(dirname "$0")/.."

echo "🚀 Starting FlexFastMCP OpenAPI Middleware Server..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install package in development mode
echo "📚 Installing package..."
pip install -e .

# Run the server
echo ""
echo "🌐 Starting Middleware Server on port ${MCP_PORT:-8080}..."
echo "==========================================="
python -m flexfastmcp
