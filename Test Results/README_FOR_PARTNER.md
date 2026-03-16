# KubeLLM Data Export — For Plotting / Analysis

Export date: use file timestamps.  
**Main data file:** `metrics_export.csv` (all rows from the experiment).

---

## What’s in the data

- **289 rows** (one row per agent run: debug or verification).
- Each **test-case run** produces **2 rows**: one for the **debug** agent, one for the **verification** agent (same `id` grouping is not in CSV; use `timestamp` + `test_case` to pair them).

---

## Column meanings

| Column | Meaning |
|--------|--------|
| `id` | Unique row ID |
| `timestamp` | When the run was recorded (ISO) |
| `test_case` | Which scenario: e.g. port_mismatch, wrong_interface, incorrect_selector, environment_variable, port_mismatch_wrong_interface, readiness_missing_dependency, selector_env_variable, resource_limits_oom |
| `model` | Model used for this row (e.g. gpt-5-nano, gpt-5-mini; no Gemini in this export) |
| `agent_type` | `debug` or `verification` |
| `input_tokens`, `output_tokens`, `total_tokens` | Token counts for that agent |
| `task_status` | Debug agent’s self-report: 1 = claimed SOLVED, 0 = FAILED/ERROR (only meaningful when `agent_type` = debug) |
| `task_status_verified` | Verification result: 1 = VERIFIED, 0 = FAILED (on both debug and verification rows for that run) |
| `duration_s` | Time in seconds for that agent call |
| `cost` | Token cost (if used) |
| `temperature` | Temperature used |
| `ground_truth` | Optional; often empty. 1 = actually fixed, 0 = not fixed (for later labeling) |

---

## Configs represented (by model)

- **Config 1:** Debug = gpt-5-nano, Knowledge + Verification = gpt-5-mini  
- **Config 3:** Knowledge + Debug = gpt-5-nano, Verification = gpt-5-mini  
- **Config 2 (Gemini debug):** Not present in this export (collection was still in progress or failed for Gemini).

So all rows here are **Config 1 and Config 3** (nano debug, gpt-5-mini verification).  
Test cases with fewer rows (e.g. selector_env_variable) had setup issues or fewer completed runs.

---

## How to use for plots

- **Success rate (debug):** For `agent_type == 'debug'`, group by `test_case` (and by config if you add a config column: e.g. by `model` for debug). Then `mean(task_status)` or count of `task_status == 1` per group.
- **Success rate (verification):** Same grouping; use `task_status_verified == 1` (you can use either debug or verification rows; verification rows have the same `task_status_verified`).
- **Time:** Use `duration_s`; average or sum per test case / per config as needed.
- **Cost:** Use `cost`; sum or average per test case / config.

Pairing debug + verification for the same “run”: match rows by **same `timestamp` and `test_case`** (one row with `agent_type=debug`, one with `agent_type=verification`).

---

## Files in this folder

- **metrics_export.csv** — Full metrics table (289 rows). Use this for all plots and analysis.
- **README_FOR_PARTNER.md** — This file.

You can zip this folder and send it; your partner can open the CSV in Excel, Python, or R and use the column descriptions above.
