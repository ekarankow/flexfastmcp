@echo off
echo Starting Meta OpenAPI MCP Server...
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate

REM Install dependencies if needed
python -c "import fastmcp" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Run the simplified meta server
echo.
echo Starting server on port 3000...
echo ================================
python meta_openapi_simple.py