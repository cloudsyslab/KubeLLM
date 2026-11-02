#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${KUBELLM_UI_PYTHON:-$repo_root/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
  python_bin="python3"
fi

if [[ -z "${KUBELLM_LAB_CONFIG:-}" ]]; then
  echo "Select a private lane first: export KUBELLM_LAB_CONFIG=<owner-only lane selector file>" >&2
  exit 2
fi

port="${KUBELLM_UI_PORT:-8787}"
exec "$python_bin" -m uvicorn operator_ui.app:app --host 127.0.0.1 --port "$port" --workers 1 --no-access-log
