#!/bin/bash
# Start the FlexFastMCP OpenAPI server in HTTP/SSE streaming mode

echo "🚀 Starting FlexFastMCP OpenAPI Server in HTTP/SSE streaming mode..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the HTTP server
echo ""
echo "🌐 Starting server..."
echo "================================"
python http_server.py