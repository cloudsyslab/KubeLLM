#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${KUBELLM_UI_PYTHON:-$repo_root/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
  python_bin="python3"
fi

if [[ ! -f "$repo_root/.local/operator_ui/auth.json" ]]; then
  echo "Set up the operator login first: $python_bin -m operator_ui.setup_auth" >&2
  exit 2
fi

port="${KUBELLM_UI_PORT:-8787}"
exec "$python_bin" -m uvicorn operator_ui.app:app --host 127.0.0.1 --port "$port" --workers 1 --no-access-log
