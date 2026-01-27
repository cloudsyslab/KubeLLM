##Runbook w/ Updates?

  1. List available tests

  python3 debug_assistant_latest/runner.py --list

  2. Run tests

  Single test:
  python3 debug_assistant_latest/runner.py wrong_port

  Multiple tests (parallel):
  python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4

  With config override:
  python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o

  3. View results

  Aggregate summary (printed automatically after run):
  cat .local/test_runs/*/aggregate.json | jq

  Specific test summary:
  cat .local/test_runs/*/<test_name>/summary.json | jq

  Full logs for a test:
  cat .local/test_runs/*/<test_name>/stdout.log

  4. Cleanup

  python3 debug_assistant_latest/teardownenv.py <test_name>
  # or
  python3 debug_assistant_latest/teardownenv.py all

  5. Find latest run

  ls -lt .local/test_runs/ | head -5