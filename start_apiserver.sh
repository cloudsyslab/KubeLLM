#!/bin/bash
# start FastAPI server on port 8501
set -a
if [[ -f ".env" ]]; then
    source .env
fi
set +a

if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "Error: OPENAI_API_KEY is not set. Add it to .env or export it before running the script."
    exit 1
fi

echo "OPENAI_API_KEY is set."

# Detect environment (Linux/Lab vs macOS/Local)
if [[ "$(uname)" == "Linux" ]]; then
    # Try common lab paths for uvicorn
    if [[ -f "/home/ubuntu/.local/bin/uvicorn" ]]; then
        UVICORN_CMD="/home/ubuntu/.local/bin/uvicorn"
    elif [[ -f "/home/minh/.local/bin/uvicorn" ]]; then
        UVICORN_CMD="/home/minh/.local/bin/uvicorn"
    else
        UVICORN_CMD="uvicorn"
    fi
else
    # macOS or other
    UVICORN_CMD="uvicorn"
fi

echo "Using uvicorn command: $UVICORN_CMD"

$UVICORN_CMD api_server:app --reload --host 0.0.0.0 --port 8501

