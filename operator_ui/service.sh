#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
state_dir="${KUBELLM_UI_STATE_DIR:-$repo_root/.local/operator_ui}"
export KUBELLM_UI_STATE_DIR="$state_dir"
pid_file="$state_dir/server.pid"
log_file="$state_dir/server.log"
port="${KUBELLM_UI_PORT:-8787}"
python_bin="${KUBELLM_UI_PYTHON:-$repo_root/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
  python_bin="python3"
fi

process_matches() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ && -r "/proc/$pid/cmdline" ]] || return 1
  tr '\0' ' ' < "/proc/$pid/cmdline" | grep -Fq 'uvicorn operator_ui.app:app'
}

read_pid() {
  [[ -f "$pid_file" && ! -L "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s' "$pid"
}

case "${1:-status}" in
  start)
    if [[ -z "${KUBELLM_LAB_CONFIG:-}" ]]; then
      echo "Select a private lane first: export KUBELLM_LAB_CONFIG=<owner-only lane selector file>" >&2
      exit 2
    fi
    umask 077
    mkdir -p "$state_dir"
    chmod 700 "$state_dir"
    if ! "$python_bin" -c 'from operator_ui.config import private_lab_config; from debug_assistant_latest.lab_context import load_lane_config; load_lane_config(private_lab_config())' >/dev/null; then
      echo "The selected lane configuration could not be validated; the operator app was not started." >&2
      exit 2
    fi
    if pid="$(read_pid 2>/dev/null)" && process_matches "$pid"; then
      echo "Operator app is already running (pid $pid, port $port)."
      exit 0
    fi
    rm -f "$pid_file"

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

    nohup "$python_bin" -m uvicorn operator_ui.app:app --host 127.0.0.1 --port "$port" --workers 1 --no-access-log >> "$log_file" 2>&1 < /dev/null &
    pid="$!"
    printf '%s\n' "$pid" > "$pid_file"
    chmod 600 "$pid_file" "$log_file"
    for _ in {1..30}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pid_file"
        echo "Operator app failed to start. See $log_file." >&2
        tail -n 30 "$log_file" >&2 || true
        exit 1
      fi
      if curl --silent --fail "http://127.0.0.1:$port/api/overview" >/dev/null; then
        echo "Operator app is running on 127.0.0.1:$port (pid $pid)."
        echo "Open the local UI through an SSH tunnel; it is not listening on the network interface."
        exit 0
      fi
      sleep 1
    done
    echo "Operator app process is alive, but its health endpoint did not respond. See $log_file." >&2
    exit 1
    ;;
  status)
    if pid="$(read_pid 2>/dev/null)" && process_matches "$pid"; then
      if curl --silent --fail "http://127.0.0.1:$port/api/overview" >/dev/null; then
        echo "Operator app is running and responding on 127.0.0.1:$port (pid $pid)."
      else
        echo "Operator app process $pid is running, but /api/overview did not respond. See $log_file."
        exit 1
      fi
    else
      echo "Operator app is not running."
      exit 1
    fi
    ;;
  stop)
    if ! pid="$(read_pid 2>/dev/null)" || ! process_matches "$pid"; then
      echo "Operator app is not running under its managed PID file."
      rm -f "$pid_file"
      exit 0
    fi
    kill -TERM "$pid"
    for _ in {1..15}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pid_file"
        echo "Operator app stopped."
        exit 0
      fi
      sleep 1
    done
    echo "Operator app did not stop within 15 seconds; PID $pid was left running." >&2
    exit 1
    ;;
  logs)
    umask 077
    mkdir -p "$state_dir"
    chmod 700 "$state_dir"
    touch "$log_file"
    chmod 600 "$log_file"
    tail -n 100 -f "$log_file"
    ;;
  *)
    echo "Usage: $0 {start|status|stop|logs}" >&2
    exit 2
    ;;
esac
