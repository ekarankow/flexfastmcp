$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "🚀 Starting FlexFastMCP OpenAPI Middleware Server..."
Write-Host ""

if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..."
    python -m venv venv
}

Write-Host "🔧 Activating virtual environment..."
& "venv\Scripts\Activate.ps1"

Write-Host "📚 Installing package..."
pip install -e .

if (-not $env:MCP_PORT) {
    $env:MCP_PORT = "8080"
}

Write-Host ""
Write-Host "🌐 Starting Middleware Server on port $env:MCP_PORT..."
Write-Host "==========================================="
python -m flexfastmcp
