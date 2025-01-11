#!/bin/bash
# start FastAPI server on port 8501
/home/ubuntu/.local/bin/uvicorn api_server:app --reload --host 0.0.0.0 --port 8501
