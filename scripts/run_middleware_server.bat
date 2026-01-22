@echo off
echo Starting FlexFastMCP OpenAPI Middleware Server...
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run the middleware server
echo.
echo Starting Middleware Server on port 3000...
echo =========================================
python fastmcp_openapi_middleware.py