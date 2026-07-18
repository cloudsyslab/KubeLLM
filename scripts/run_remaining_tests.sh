#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "debug_assistant_latest/runner.py" ]]; then
  echo "Run this script from the KubeLLM repository root." >&2
  exit 1
fi

remaining_cases=(
  "liveness_probe"
  "wrong_port_7001"
  "wrong_port_9090"
)

failed_cases=()

for test_case in "${remaining_cases[@]}"; do
  echo "=== Running ${test_case} ==="
  if ! python3 debug_assistant_latest/runner.py "${test_case}" \
    --api-model gpt-5-mini \
    --debug-model gpt-5-nano \
    --verification-model gpt-5-nano \
    --minikube-profile plama \
    --teardown-after-run; then
    failed_cases+=("${test_case}")
    echo "=== ${test_case} failed; continuing with remaining cases ===" >&2
  fi
done

if (( ${#failed_cases[@]} > 0 )); then
  echo "Completed with failing test cases: ${failed_cases[*]}" >&2
  exit 1
fi

echo "All remaining test cases completed."
