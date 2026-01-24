#!/usr/bin/env bash
set -euo pipefail

KUBECONFIG_PATH="${KUBECONFIG_PATH:-$HOME/.kube/minh-admin.conf}"
OUT_DIR=".local/diagnostics/$(date -u +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

run_cmd() {
  local name="$1"
  shift
  echo "==> $*" >> "$OUT_DIR/commands.log"
  "$@" > "$OUT_DIR/$name.txt" 2>&1 || true
}

run_cmd "namespaces" kubectl --kubeconfig "$KUBECONFIG_PATH" get ns -o wide
run_cmd "nodes" kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes -o wide
run_cmd "pods_all" kubectl --kubeconfig "$KUBECONFIG_PATH" get pods -A -o wide
run_cmd "svc_all" kubectl --kubeconfig "$KUBECONFIG_PATH" get svc -A -o wide
run_cmd "deploy_all" kubectl --kubeconfig "$KUBECONFIG_PATH" get deploy -A -o wide
run_cmd "events_all" kubectl --kubeconfig "$KUBECONFIG_PATH" get events -A --sort-by=.lastTimestamp

namespaces=$(kubectl --kubeconfig "$KUBECONFIG_PATH" get ns -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)
for ns in $namespaces; do
  pods=$(kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$ns" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)
  for pod in $pods; do
    run_cmd "describe_pod_${ns}_${pod}" kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$ns" describe pod "$pod"
    run_cmd "logs_${ns}_${pod}" kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$ns" logs "$pod" --all-containers=true --tail=200
    run_cmd "logs_prev_${ns}_${pod}" kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$ns" logs "$pod" --previous --all-containers=true --tail=200
  done
done

echo "$OUT_DIR"
