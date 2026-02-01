## Runbook

  1. List available tests

  python3 debug_assistant_latest/runner.py --list

  2. Run tests

  Single test:
  python3 debug_assistant_latest/runner.py wrong_port

  Multiple tests (parallel):
  python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4

  With config override:
  python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o

  Repeat queue (serial with teardown + hard-kill on stall):
  python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900

  Repeat queue with explicit output dir:
  python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --output-dir /tmp/kubellm_runs

  Minikube profile override (only applied when explicitly passed):
  python3 debug_assistant_latest/runner.py wrong_port --minikube-profile minh

  3. View results

  Aggregate summary (printed automatically after run):
  cat .local/test_runs/*/aggregate.json | jq

  Specific test summary:
  cat .local/test_runs/*/<test_name>/summary.json | jq

  Full logs for a test:
  cat .local/test_runs/*/<test_name>/stdout.log

  Repeat queue summary:
  cat .local/test_runs/<queue_id>/queue_summary.json | jq

  4. Cleanup

  python3 debug_assistant_latest/teardownenv.py <test_name>
  # or
  python3 debug_assistant_latest/teardownenv.py all

  5. Find latest run

  ls -lt .local/test_runs/ | head -5

  6. Repeat queue output layout

  Without --output-dir:
  .local/test_runs/<queue_id>/
    queue_summary.json
    iter-001/
    iter-002/
    ...

  With --output-dir /some/path:
  /some/path/<queue_id>/
    queue_summary.json
    iter-001/
    iter-002/
    ...
