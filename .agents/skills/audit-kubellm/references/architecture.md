# KubeLLM architecture

KubeLLM is a Python benchmark harness, not a general-purpose cluster
controller. Its canonical interface is `debug_assistant_latest/runner.py`.
The runner owns case discovery, configuration, readiness, setup, execution,
evaluation, reports, diagnosis, and teardown.

```text
runner.py -> preflight -> case setup -> selected technique
                                      |  Knowledge Agent / RAG
                                      |  strategy-specific execution
                                      v
                         Verification (where configured)
                                      + Ground Truth (when configured)
                                      v
                   summary.json + aggregate.json + run_config.json
```

## Main components

| Area | Source | Role |
|---|---|---|
| Runner and case discovery | `runner.py`, `test_discovery.py` | CLI, test listing, preflight, run orchestration, queues, diagnosis, reports |
| Strategy orchestration | `main.py`, `executor.py` | Selects agent path, handles outcomes, invokes evaluators and teardown |
| Knowledge and RAG | `api_agents.py`, `rag_api.py`, `api_server.py`, `assistant.py` | Retrieve Kubernetes guidance through the FastAPI service and pgvector |
| Generative execution | `debug_agents.py`, `better_shell.py` | Apply fixes with shell and file tools for the agent-driven strategies |
| Deterministic plan POC | `knowledge_agent_only.py` | Validate strict JSON instructions and execute commands sequentially without a Tools Agent reasoning step |
| Evaluation | `verification_agents.py`, `ground_truth.py` | Independent LLM verification and deterministic configured checks |
| Lab isolation | `lab_context.py`, `preflight.py` | Validate explicit lane targets, serial execution, services, dependencies, and cluster readiness |
| Evidence | `report.py`, `result_interpreter.py`, `dashboard.py` | Store run summaries and classify or summarize outcomes |
| Fixtures and teardown | `troubleshooting/`, `teardown.py` | Define broken cases, expected checks, restoration, and cleanup |

## Technique differences

- `allStepsAtOnce`: Knowledge Agent guidance is passed to a generative Tools
  Agent for diagnosis and execution; Verification and configured Ground Truth
  follow.
- `stepByStep`: Knowledge guidance is executed incrementally by the
  step-by-step Tools Agent; configured evaluators follow.
- `singleAgent`: one generative agent diagnoses and acts; configured Ground
  Truth runs, with the verification stage omitted by design.
- `knowledgeAgentOnly`: the Knowledge Agent returns a schema-constrained
  command plan. The parser validates the whole plan, the existing executor
  runs it sequentially, then independent Verification and configured Ground
  Truth run. No repair reasoning, plan rewrite, or retry is added.

Do not conflate architecture execution with task success. A valid plan that
ran is not proof the issue was fixed. When configured, deterministic Ground
Truth is authoritative; Verification and agent self-report are separate
signals. Keep generation, contract, execution, Verification, Ground Truth,
and readiness failures diagnosable as distinct stages.

Per-run evidence is written under ignored `.local/test_runs/`. A typical case
has `summary.json`, `config_effective.json`, optional `ground_truth.json`, and
logs; run-level files include `aggregate.json` and `run_config.json`.
`knowledgeAgentOnly` also writes a raw Knowledge response and a
`knowledge_execution.json`; treat command content and raw output as sensitive
and do not paste them into public reports.
