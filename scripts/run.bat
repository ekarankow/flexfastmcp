@echo off
REM Run the FlexFastMCP OpenAPI Middleware Server

cd /d "%~dp0\.."

echo 🚀 Starting FlexFastMCP OpenAPI Middleware Server...
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install package in development mode
echo 📚 Installing package...
pip install -e .

REM Run the server
echo.
if not defined MCP_PORT set MCP_PORT=3000
echo 🌐 Starting Middleware Server on port %MCP_PORT%...
echo ===========================================
python -m fastmcp_openapi
