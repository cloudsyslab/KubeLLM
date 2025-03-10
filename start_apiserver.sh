#!/bin/bash
# start FastAPI server on port 8501
if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "Error: OPENAI_API_KEY is not set. Please set it before running the script."
    exit 1
fi

echo "OPENAI_API_KEY is set."

/home/ubuntu/.local/bin/uvicorn api_server:app --reload --host 0.0.0.0 --port 8501
