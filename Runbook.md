## Runbook (Lab-Only)

LAB-ONLY EXECUTION: All tests and operational commands must be run on the lab server.
Local runs are for development/editing only.

### 0) After SSH to the lab server

1) Go to the repo:
```
cd ~/kubellm-minh-testing
```

2) Confirm repo is up to date:
```
git status -sb
git pull
```

### 1) Preflight (always required before any test run)

```
bash orchestrator/preflight.sh
```

Expected: API ready and `kubectl get nodes` succeeds.

### 2) List tests

```
python3 debug_assistant_latest/runner.py --list
```

### 3) Run tests (recommended: runner.py)

Single test:
```
python3 debug_assistant_latest/runner.py wrong_port
```

Multiple tests (parallel):
```
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4
```

With config override:
```
python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o
```

Repeat queue (serial with teardown + hard-kill on stall):
```
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900
```

Repeat queue with explicit output dir:
```
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --output-dir /tmp/kubellm_runs
```

Minikube profile override (only applied when explicitly passed):
```
python3 debug_assistant_latest/runner.py wrong_port --minikube-profile minh
```

### 4) View results

Aggregate summary (printed automatically after run):
```
cat .local/test_runs/*/aggregate.json | jq
```

Specific test summary:
```
cat .local/test_runs/*/<test_name>/summary.json | jq
```

Full logs for a test:
```
cat .local/test_runs/*/<test_name>/stdout.log
```

Repeat queue summary:
```
cat .local/test_runs/<queue_id>/queue_summary.json | jq
```

### 5) Cleanup

```
python3 debug_assistant_latest/teardownenv.py <test_name>
```
or:
```
python3 debug_assistant_latest/teardownenv.py all
```

### 6) Find latest run

```
ls -lt .local/test_runs/ | head -5
```

### 7) Repeat queue output layout

Without --output-dir:
```
.local/test_runs/<queue_id>/
  queue_summary.json
  iter-001/
  iter-002/
  ...
```

With --output-dir /some/path:
```
/some/path/<queue_id>/
  queue_summary.json
  iter-001/
  iter-002/
  ...
```
