# Data for Poster — KubeLLM Experiment

Send your partner the **`data_export`** folder (or zip it). Everything needed for the poster is here.

**Start here for building figures:** `POSTER_FIGURES_AND_FOOTERS.md` — lists each graph, which file to use, and **Key Findings** footer text for each figure.

---

## What’s in this export

- **Configs in the data:** All rows are from runs where **debug agent = gpt-5-nano** and **verification agent = gpt-5-mini** (Config 1 and Config 3 style; Config 2 with Gemini had quota/API issues and is not included).
- **Test cases:** port_mismatch, wrong_interface, incorrect_selector, environment_variable, port_mismatch_wrong_interface, readiness_missing_dependency, selector_env_variable, resource_limits_oom (selector_env_variable has only 1 run).

---

## Files to use for the poster

### Figure 1 — Success rate (Y = Success rate, X = Model combinations, bar graph)
- **poster_success_by_model.csv** — `success_before_verification`, `success_after_verification` by `model_combination`.

### Figure 2 — Cost (Y = Cost, X = Model combination, bar graph)
- **poster_cost_by_model.csv** — `cost_before_verification_total` / `avg_cost_per_run_before` and `cost_after_verification_total` / `avg_cost_per_run_after` by `model_combination`.

### Figure 3 — Average task completion time (text, not graph)
- **poster_time_summary.txt** — Numbers for “with and without verification” to write in text.

### Key Findings (footer for each figure)
- **POSTER_FIGURES_AND_FOOTERS.md** — Ready-to-use footer text for each figure.

---

### 1. **metrics_full.csv** — Raw data (289 rows)

Every run: one row per agent (debug or verification). Use this for custom plots or checks.

| Column | Meaning |
|--------|--------|
| `test_case` | Scenario name |
| `model` | gpt-5-nano (debug) or gpt-5-mini (verification) |
| `agent_type` | debug or verification |
| `task_status` | 1 = debug claimed SOLVED, 0 = failed (use only on debug rows) |
| `task_status_verified` | 1 = VERIFIED, 0 = failed, -1 = error (verification result for that run) |
| `duration_s` | Time in seconds for that agent call |
| `cost` | Token cost for that call |
| `total_tokens` | Input + output tokens |

Pairing: same run = same `timestamp` + `test_case` (one debug row, one verification row).

---

### 2. **poster_success_rates.csv** — For bar charts (success rates)

One row per test case. Use for **“success rate”** bar charts.

| Column | Meaning |
|--------|--------|
| `test_case` | Scenario name |
| `n_runs` | Number of runs for that test case |
| `debug_success_rate` | Fraction of runs where debug agent claimed SOLVED (0–1) |
| `verified_success_rate` | Fraction of runs where verification said VERIFIED (0–1) |

**Poster idea:** Bar chart with test_case on x-axis, two bars per test case: “Debug (self-report)” and “Verification”. Use `debug_success_rate` and `verified_success_rate` as heights.

---

### 3. **poster_time_and_cost.csv** — For time and cost plots

One row per test case. Use for **“time taken”** and **“token cost”** plots.

| Column | Meaning |
|--------|--------|
| `test_case` | Scenario name |
| `avg_duration_s` | Average duration (seconds) per run (debug + verification) |
| `total_cost` | Total token cost across all runs for that test case |
| `total_tokens` | Total tokens across all runs |

**Poster ideas:** Bar chart of `avg_duration_s` by test_case; bar chart of `total_cost` (or cost per run = total_cost / n_runs from success_rates) by test_case.

---

## Quick reference for plotting

- **Success rate (debug vs verification):** Use `poster_success_rates.csv` → bars: `debug_success_rate`, `verified_success_rate` by `test_case`.
- **Time taken:** Use `poster_time_and_cost.csv` → bar or line: `avg_duration_s` by `test_case`.
- **Token cost:** Use `poster_time_and_cost.csv` → bar: `total_cost` (or divide by n_runs from success_rates for per-run cost) by `test_case`.
- **Test cases:** Delineate by `test_case` in all files.

---

## Note on configs

This export has only **nano debug + gpt-5-mini verification** (no Gemini debug). So the “3 model combinations” bar chart on the poster will show only the data we have; Config 2 (Gemini) can be labeled as “N/A” or omitted if you don’t add that data later.
