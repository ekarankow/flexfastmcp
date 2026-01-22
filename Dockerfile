# Use Python slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Install the package in editable mode without re-resolving deps
RUN pip install --no-cache-dir -e . --no-deps
#COPY openapi.json ./

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose MCP default port
EXPOSE 3000

# Run the MCP middleware server
CMD ["python", "-m", "fastmcp_openapi"]