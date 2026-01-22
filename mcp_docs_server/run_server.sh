#!/bin/bash
# Wrapper script to run the KubeLLM MCP docs server with proper venv activation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to include parent directory
export PYTHONPATH="${SCRIPT_DIR}/.."

# Run the MCP server
exec python -m mcp_docs_server
