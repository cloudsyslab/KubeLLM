#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
web_dir="$repo_root/operator_ui/web"
node_bin="${KUBELLM_UI_NODE_BIN:-$HOME/.local/share/nodejs/node-v24.20.0-linux-x64/bin/node}"
if [[ ! -x "$node_bin" ]]; then
  node_bin="$(command -v node || true)"
fi
if [[ -z "$node_bin" || ! -x "$node_bin" ]]; then
  echo "Node 20 or newer is required to build operator_ui/web." >&2
  exit 2
fi
node_version="$("$node_bin" --version | sed 's/^v//')"
node_major="${node_version%%.*}"
if [[ ! "$node_major" =~ ^[0-9]+$ || "$node_major" -lt 20 ]]; then
  echo "Node 20 or newer is required; found $node_version." >&2
  exit 2
fi
npm_bin="$(dirname "$node_bin")/npm"
if [[ ! -x "$npm_bin" ]]; then
  echo "npm was not found beside $node_bin." >&2
  exit 2
fi
(
  cd "$web_dir"
  PATH="$(dirname "$node_bin"):$PATH" "$npm_bin" ci
  PATH="$(dirname "$node_bin"):$PATH" VITE_OPERATOR_DATA=api "$npm_bin" run build
)
