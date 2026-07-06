python3 debug_assistant_latest/runner.py \
--run-many '*' \
--api-model gpt-5-mini \
--debug-model qwen3-coder:30b \
--verification-model qwen3-coder:30b \
--minikube-profile plama \
--backup-before-run \
--teardown-after-run

python3 debug_assistant_latest/runner.py \
--run-many '*' \
--api-model gpt-5-mini \
--debug-model nemotron-cascade-2:30b \
--verification-model nemotron-cascade-2:30b \
--minikube-profile plama \
--backup-before-run \
--teardown-after-run

python3 debug_assistant_latest/runner.py \
--run-many '*' \
--api-model gpt-5-mini \
--debug-model glm-4.7-flash:latest \
--verification-model glm-4.7-flash:latest \
--minikube-profile plama \
--backup-before-run \
--teardown-after-run

