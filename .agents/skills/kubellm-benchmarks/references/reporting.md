# Benchmark reports

Every requested run ends with benchmark_summary.md. Include the same report when analyzing an existing run or export. The generated Markdown follows this order:

1. Title and session or run identifier, requested cases, iterations, observed and expected executions, runtime, and configuration.
2. Executive results.
3. Results by case.
4. Iteration variation.
5. Recorded cost and token use.
6. Notable findings and integrity risks.
7. Recommended interpretation.

## Outcomes and denominators

- Configured deterministic Ground Truth is the task outcome.
- Count a Ground Truth pass only when the recorded outcome is true. Report its rate across all recorded attempts and separately across known Ground Truth evaluations. Missing Ground Truth remains unavailable; do not infer it from Verification, status, agent output, or expected results.
- Show Verification success reports across attempts and among returned verdicts. Its correctness metrics use only attempts with both a Ground Truth result and verifier verdict.
- Define verifier true positives as verified and Ground-Truth passing; true negatives as both failing; false positives as verified with Ground-Truth failure; and false negatives as unverified with Ground-Truth success. Keep missing verdicts visible outside that matrix.
- Report runner PASS, FAIL, ERROR, and TIMEOUT independently. Do not use runner PASS as Ground Truth.
- Report debug-agent self-report separately. If comparing it with Ground Truth, use the same confusion-matrix definitions and matched observations.
- For each case, show the observed Ground-Truth and Verification successes against their explicit denominator, plus false positives, false negatives, unavailable verdicts, errors/timeouts, and available average recorded cost. Never make an unattempted case look like a failure or success.
- For each iteration, report its actual attempted and evaluated counts, success rates, and recorded cost. Preserve partially recorded and unstarted iterations explicitly.

## Cost and tokens

Use the recorded per-agent metrics. Identify the API/Knowledge, debug, and Verification totals separately; also report the sum of available recorded agent costs, tokens by agent, per-attempt and per-iteration averages, and cost per Ground-Truth success only when those denominators exist. Show per-agent metric coverage. If any agent metric is absent, label the combined sum as partial and exclude the missing use; never describe partial totals as fully costed. Do not treat a recorded zero as proof that computation was free.

## Findings and source evidence

Generate the numeric tables and integrity counts with summarize_run.py. Enrich findings using only inspected structured artifacts and relevant case evidence. Cite case evidence with run-relative artifact names such as iter-003/case-name/ground_truth.json; never include absolute machine paths.

Useful grounded findings include verifier disagreements concentrated in specific cases, recurring failed Ground-Truth checks, known architecture-stage errors, queue stops and unstarted cases, aggregate/report mismatches, missing artifacts, dirty or mixed source revisions, uneven case success, and cost outliers. State what the evidence establishes and what it cannot establish. Do not diagnose a cause from correlation alone.

Report queue completion against planned iterations. Compare aggregate counts and metrics against parsed case files. State each validation finding by severity and code, without copying free-form error details or raw logs.

For repeated cases, discuss iteration variation descriptively. Five repetitions can reveal instability but do not precisely estimate an underlying probability. Do not claim significance or a general technique winner from a single or incomplete suite.

## Privacy and preservation

For a new run, write the generated report beside its ignored source artifacts and copy the reviewed Markdown report into that run's `data/` pack during publication. For analysis-only work on tracked data, write to `.local/benchmark_reports/` unless the user selects another destination. Do not modify source summaries or aggregates.

Never include secrets, private lane selectors or profile names, service endpoints, environment variables, raw prompts, raw tool output, free-form exception text, knowledge plans, or absolute paths. Model identifiers, technique, case names, hashes, counts, and numeric metrics may be included after validating their field and shape.

Leave all source case summaries and aggregates unchanged. Missing, malformed, or inconsistent artifacts are report findings, not invitations to repair historical data.
