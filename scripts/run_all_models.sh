#!/usr/bin/env bash
set -euo pipefail

runner_lane_args=(--minikube-profile "${MINIKUBE_PROFILE:-plama}")
if [[ -n "${KUBELLM_LAB_CONFIG:-}" ]]; then
  runner_lane_args=(--lab-config "$KUBELLM_LAB_CONFIG")
fi

python3 debug_assistant_latest/runner.py \
--run-many '*' \
--api-model gpt-5-mini \
--debug-model qwen3-coder:30b \
--verification-model qwen3-coder:30b \
"${runner_lane_args[@]}" \
--teardown-after-run

python3 debug_assistant_latest/runner.py \
--run-many '*' \
--api-model gpt-5-mini \
--debug-model nemotron-cascade-2:30b \
--verification-model nemotron-cascade-2:30b \
"${runner_lane_args[@]}" \
--teardown-after-run

python3 debug_assistant_latest/runner.py \
--run-many '*' \
--api-model gpt-5-mini \
--debug-model glm-4.7-flash:latest \
--verification-model glm-4.7-flash:latest \
"${runner_lane_args[@]}" \
--teardown-after-run
