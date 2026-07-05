#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "debug_assistant_latest/runner.py" ]]; then
  echo "Run this script from the KubeLLM repository root." >&2
  exit 1
fi

remaining_cases=(
  "environment_variable_wrong_name"
  "incorrect_selector_missing_label"
  "liveness_probe_wrong_path"
  "missing_dependency_requirements"
  "port_mismatch_named_target"
  "readiness_failure_slow_start"
  "readiness_missing_dependency_transitive"
  "resource_limits_cpu_starvation"
  "selector_env_variable_label_and_secret"
)

failed_cases=()

for test_case in "${remaining_cases[@]}"; do
  echo "=== Running ${test_case} ==="
  if ! python3 debug_assistant_latest/runner.py "${test_case}" \
    --api-model gpt-5-mini \
    --debug-model gpt-5-nano \
    --verification-model gpt-5-nano \
    --minikube-profile plama \
    --backup-before-run \
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
