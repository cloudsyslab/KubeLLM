#!/bin/bash
set -euo pipefail

if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
fi

python start_apiserver.py "$@"
