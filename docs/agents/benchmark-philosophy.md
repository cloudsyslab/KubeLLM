# Benchmark philosophy

Read this before modifying agents, prompts, test cases, or verification logic.

## What KubeLLM is

KubeLLM is a **measurement instrument**. It exists to answer one question: *How well can a given LLM diagnose and fix real Kubernetes issues?*

It is not a product. There is no user to satisfy and no success rate to maximize. A model that fails 12 out of 13 tests has produced valid, useful data. A benchmark that has been tuned so every model passes has produced nothing.

The value of this project is **accuracy of measurement**, not outcomes.

## What is being measured

Given a broken Kubernetes deployment and a natural-language description of the symptoms, the model must:

1. Use a knowledge base (RAG) to research the problem -- the same way an SRE would consult documentation
2. Diagnose the root cause from cluster state, logs, manifests, and application code
3. Execute a fix using shell commands and file edits
4. The fix is then evaluated independently by verification agents and deterministic checks

The model receives symptoms ("the pod cannot be accessed, curl times out") and tooling (kubectl, file access, RAG). It does not receive the answer.

## The four agents

| Agent | Role | Analogy |
|-------|------|---------|
| **Knowledge Agent** | Queries a RAG knowledge base with the problem description and returns troubleshooting guidance | An SRE reading documentation and runbooks before touching the cluster |
| **Debug Agent** | Receives the knowledge agent's guidance plus direct file/cluster access, then diagnoses and executes a fix | The SRE doing the actual work -- this is the model under test |
| **Verification Agent** | An independent LLM that checks cluster state after the debug agent finishes, with no knowledge of what the debug agent tried | A second engineer reviewing whether the issue is actually resolved |
| **Ground Truth** | Deterministic shell commands that check specific conditions (pod ready, port correct, HTTP 200, etc.) | An automated test suite -- the final authority |

Every agent exists for a reason. The Knowledge Agent is not a shortcut -- it represents the realistic advantage of having a knowledge base. The Verification Agent is not redundant with Ground Truth -- it tests whether a model can evaluate cluster state, which is itself a measurable capability.

## Verification hierarchy

Three layers, in order of authority:

1. **Ground Truth** (deterministic) -- Highest authority. Shell commands with polling, exact-value checks, regex, numeric thresholds. If ground truth says FAIL, the test failed. Period.
2. **Verification Agent** (LLM) -- Independent check. Useful signal, but can be wrong. Does not override ground truth.
3. **Debug Agent self-report** (LLM) -- Weakest signal. The model's own claim about whether it succeeded. Recorded for analysis, never trusted as the final word.

This layering exists because models are unreliable self-evaluators. A model that reports `<|SOLVED|>` while the pod is still crashing has not solved anything. Ground truth catches this.

## Rules for modifying this codebase

### Prompts must describe symptoms, never solutions

A test prompt should read like a user's bug report: what they observe, what they expected, what went wrong. It must never contain:

- The root cause ("the port is wrong")
- The fix ("change containerPort to 8765")
- Specific values that constitute the answer
- Commands that would solve the problem

**Good:** "The pod cannot be accessed by making a curl request. Requests to the application result in a timeout."

**Bad:** "The pod uses containerPort 8000 but the server listens on 8765. Change the port."

If an agent working on this codebase cannot tell the difference between a symptom and a solution, it should not modify prompts.

### Do not optimize for pass rates

The following changes are **always wrong** if their purpose is to make tests pass more often:

- Making prompts more specific or hint-like so the model gets the answer faster
- Adding retries or fallbacks that mask model failures
- Weakening ground truth checks so partial fixes count as passes
- Adding model-specific prompt tuning (different hints for different models)
- Reducing test difficulty or removing hard test cases from the suite

A change that makes a test easier is not a fix. It is data corruption.

### Do not bypass the model

The model must do the work. The following patterns are prohibited:

- Hardcoding the fix in agent code and executing it instead of letting the model reason (e.g., scripting PowerShell commands that apply the correct answer)
- Short-circuiting the debug loop when deterministic checks detect the right state was reached by something other than model action
- Platform-specific code paths that skip the LLM on certain operating systems
- Pre-computing the answer and injecting it into the model's context

If the model cannot solve a problem on a given platform, that is a valid result. The benchmark should record it, not hide it.

### Do not conflate evaluator quality with benchmark quality

The Verification Agent and Ground Truth exist to evaluate the debug agent's work. Changes to evaluators should make them more accurate, not more lenient. Specifically:

- Verification agent temperature should be high ALWAYS (1) -- evaluators should be deterministic
- Ground truth checks should be precise and sufficient -- if a check can be satisfied without the actual fix being applied, the check is wrong
- New ground truth checks should cover the specific fix, not just "pod is running" (a pod can be running with the original bug)

### Test cases must be reproducible

Every test starts from the same broken state. This means:

- Setup commands in `config_step.json` must fully recreate the broken scenario from scratch
- Teardown must restore the environment to pre-test state
- No test should depend on state left by a previous test
- Fixture files (manifests, application code) in `troubleshooting/` are the source of truth -- they define the broken state

### Adding new test cases

A new test case needs:

1. A broken scenario (manifest, app code, Dockerfile) under `debug_assistant_latest/troubleshooting/<test_name>/`
2. A `config_step.json` with symptom-only problem description, setup commands, and relevant file references
3. Ground truth checks that verify the specific fix, not just general health
4. A teardown entry in `TEARDOWN_CONFIG`
5. Verification that it appears in `--list` output

The test should be designed so that a model with genuine K8s troubleshooting ability can solve it, and a model without that ability cannot. If every model solves it trivially, it is not measuring anything. If no model can solve it, it may still be valuable as a ceiling marker -- but document that intent.

## Multi-run reporting

When you publish or compare numbers from this harness, treat stochastic agents honestly:

- Report **N** (iteration count or distinct run directories), not a single lucky pass.
- Prefer an explicit aggregation (median, pass@k, failure rate with CI) and state it in the write-up.
- Use `queue_summary.json` from `--repeat` queues for iteration-level pointers (`output_dir`, `run_config_path`, `cli_overrides`); avoid headline metrics from one “hero” run unless you label them as anecdotal.

## Summary

This benchmark exists to produce honest data about model capabilities. Every design decision -- from the agent architecture to the prompt wording to the verification layers -- serves that goal. When in doubt about a change, ask: *Does this make the measurement more accurate, or does it make the number look better?* Only the first kind of change belongs here.
