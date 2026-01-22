#!/bin/bash
# Run the FlexFastMCP OpenAPI Middleware Server

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

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Run the middleware server
echo ""
echo "🌐 Starting Middleware Server on port 3000..."
echo "==========================================="
python fastmcp_openapi_middleware.py