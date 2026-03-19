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

/home/ubuntu/.local/bin/uvicorn api_server:app --reload --host 0.0.0.0 --port 8501
