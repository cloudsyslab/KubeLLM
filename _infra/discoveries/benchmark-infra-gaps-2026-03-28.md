# Discovery: benchmark infrastructure gaps (post-taxonomy)

**Date:** 2026-03-28  
**Prior artifact:** [_infra/improved-prompts/benchmark-refactor-taxonomy-2026-03-28.md](../improved-prompts/benchmark-refactor-taxonomy-2026-03-28.md)  
**Repo anchor:** [docs/benchmark-philosophy.md](../../docs/benchmark-philosophy.md)

---

## Stage 1 — Framed question

| Field | Content |
| --- | --- |
| **Subject** | How to strengthen KubeLLM’s benchmark **integrity**, **auditability**, and **scalable execution** using current industry and research norms—beyond what the repo-grounded taxonomy already listed. |
| **User context** | Single-machine runner with `.local/test_runs/`, optional parallelism, three-layer verification (ground truth → verification LLM → self-report), 13 troubleshooting scenarios. |
| **Decision supported** | Prioritizing refactor work: what to build next, what to avoid, and which external patterns to adopt or adapt. |
| **Assumptions** | Measurement fidelity remains the north star (not pass-rate optimization). Primary executor stays developer/CI on real or Minikube clusters; no product SLA implied. |

---

## Executive summary (one paragraph)

The taxonomy correctly centers **reproducibility**, **evaluator separation**, and **artifact completeness**. External practice reinforces three themes: (1) **provenance bundles**—every run should pin code, config, cluster, and dependency identity the way serious ML evaluation (e.g. holistic, multi-scenario frameworks) and agent-evaluation research treat **versioned harnesses and traces**; (2) **isolation and flakiness hygiene**—parallel integration benchmarks fail for predictable reasons (shared cluster objects, timing, order), and mature pipelines **quarantine or structurally isolate** rather than silently retrying failures into “green”; (3) **structured observability**—OpenTelemetry’s **Gen AI semantic conventions** offer a vendor-neutral shape for spans and metrics, with **privacy-first** defaults that matter when logs might contain cluster secrets. This report enlarges the gap list, compares logging/lineage options, and names **disregarded** shortcuts that would corrupt measurement.

---

## Stage 2 — Evidence gathered (sources)

| Source | What it contributed |
| --- | --- |
| [OpenTelemetry: Gen AI spans (semantic conventions)](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) | Standard attributes for model operations (`gen_ai.operation.name`, provider, model id), trace-oriented structure, and **explicit guidance that prompt/completion content is sensitive**—often omitted or referenced externally. Useful pattern for normalizing “what to log” without mandating raw text in every artifact. |
| [OpenTelemetry blog: Generative AI](https://opentelemetry.io/blog/2024/otel-generative-ai) | Frames traces + metrics + events as the three signals for GenAI observability; supports treating KubeLLM runs as exportable telemetry, not only flat files. |
| [CRFM HELM documentation](https://crfm-helm.readthedocs.io/en/stable/) | Mature **evaluation harness** mindset: standardized scenarios, transparent reporting, multi-metric comparison—analog for “benchmark is a productized harness,” not ad hoc scripts. |
| Practitioner literature on **flaky tests** and **parallel integration isolation** (e.g. shared state, resource collisions, order dependence—summarized widely in 2025–2026 testing guides) | Validates taxonomy risks on `--jobs` + overlapping K8s names; reinforces **unique resources per worker** or **hard isolation** as the real fix, not “hope.” |
| Agent-eval research threads (e.g. reproducibility-focused agent benchmarks, standardized parallel VM harnesses—see arXiv landscape 2025–2026) | **Shortcut detection** and **structured execution traces** are recurring themes; aligns with logging enough to audit “did the model actually fix the cluster vs. get lucky.” |

*Inference vs fact:* Exact HELM statistical policies for *n* runs per prompt were not re-verified from primary docs in this pass; treat “run variance / multiple seeds” below as **recommended practice** from general eval hygiene, not a HELM-specific claim.

---

## Stage 3 — Alternatives (logging and lineage)

| Criterion | A: Enrich current JSON bundle | B: OpenTelemetry export | C: Full experiment platform (MLflow-style) |
| --- | --- | --- | --- |
| **Fit for current context** | High—extends `run_config.json`, `summary.json`, `ground_truth.json` | Medium—adds SDK + exporter; fits if you already run Jaeger/Grafana | Low–medium—heavy ops unless you need cross-project dashboards |
| **Complexity** | Low | Medium | High |
| **Operating cost** | Disk + git LFS if large | Backend + retention policy | Highest |
| **Risk** | Schema drift without a version field | Misconfiguration leaks prompts if content capture on | Overkill; may tempt “optimize dashboard green” |
| **Best for** | Fast integrity wins, offline analysis | Cross-run queries, standard dashboards | Multi-team, long historical studies |
| **Avoid when** | You need interactive trace UI out of the box | Team cannot run a collector | You want to stay lightweight and local-first |

**Recommendation:** **A now, B optional, C only if scale demands.** Implement a small **run manifest schema** (provenance) first; add OTEL export only if you need standard tooling or federated analysis.

---

## Stage 4 — Gap analysis (expanded)

Gaps below **build on** the taxonomy; “Current” references the repo state described there.

### Gap: Run provenance bundle

- **Current:** Timestamps and `config_effective.json` exist; **git commit, cluster version, kubectl context, Minikube profile, and fixture digest** are not first-class mandatory fields in the run root.
- **Better approach:** Require `provenance.json` (or extend `run_config.json`) with: `git_commit`, `dirty` flag, `k8s_server_version`, `kubectl_context`, optional `minikube_profile`, hash of `troubleshooting/<test>/` inputs, `ground_truth_schema` version.
- **Impact:** High  
- **Effort:** Medium  
- **Source:** HELM-style harness transparency; general reproducibility practice.

### Gap: Statistical treatment of stochastic agents

- **Current:** `--repeat` supports serial repeats; reporting aggregates exist; **no documented policy** for how many runs, seeds, or temperature draws constitute a published number.
- **Better approach:** Document **reporting standard**: e.g. median + IQR over *n* runs, or pass@k; store `run_index` / `seed` when APIs support it; never collapse to a single heroic run for publications.
- **Impact:** High (for external credibility)  
- **Effort:** Low (docs + small schema) to High (API seed plumbing)  
- **Source:** Inference from eval best practice; aligns with philosophy (“honest data”).

### Gap: Flaky-test policy for benchmarks (not the same as product CI)

- **Current:** Flakiness risks identified (K8s timing, teardown, parallelism); no explicit **flaky-test register** or isolation SLO.
- **Better approach:** **Product CI** often quarantines flaky tests; **benchmarks** should **label** flakiness and fix root cause, not hide failures. Maintain `FLAKY.md` or machine-readable `flaky.json` with last-seen rate, linked to issue—distinct from “retry until pass.”
- **Impact:** Medium  
- **Effort:** Low  
- **Source:** Flaky-test literature; adapted for measurement ethics ([docs/benchmark-philosophy.md](../../docs/benchmark-philosophy.md) forbids masking failures).

### Gap: Parallel execution isolation contract

- **Current:** Warning in `parallel.py` about overlapping resources; operator must choose `--jobs 1` or disjoint tests.
- **Better approach:** Pick and document one: **namespace-per-run** injection, **name suffix** from `RUN_ID`, or **certified disjoint test sets** for `--jobs > 1`. Encode in preflight when possible.
- **Impact:** High for honest parallel scale  
- **Effort:** Medium–High  
- **Source:** Parallel integration testing norms (unique resources per worker).

### Gap: Structured LLM telemetry (optional OTEL)

- **Current:** stdout/stderr + optional `KUBELLM_AGENT_DEBUG_LOGS`; metrics in `summary.json` and `token_metrics.db`.
- **Better approach:** Map phases (knowledge / debug / verification / ground-truth) to **spans** with `gen_ai.*` attributes; keep **content off-spans by default**, store references or redacted hashes. Unifies token/latency/cost with hierarchy.
- **Impact:** Medium (interoperability, future tooling)  
- **Effort:** Medium  
- **Source:** [OpenTelemetry Gen AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/).

### Gap: Verification artifact parity with ground truth

- **Current:** `ground_truth.json` is durable; verification **raw report** persistence is called out as uncertain in taxonomy open questions.
- **Better approach:** Always write `verification_report.txt` (or JSON) when verification runs, alongside parsed status—enables disagreement mining without re-invoking the model.
- **Impact:** Medium  
- **Effort:** Low  
- **Source:** Three-layer hierarchy requires auditable middle layer.

### Gap: Evaluator configuration alignment

- **Current:** Example configs with verification `temperature: 1` conflict with philosophy (low temperature for evaluators).
- **Better approach:** Schema or linter warning when `verification-agent.temperature` > 0.3; document exception process if ever needed.
- **Impact:** Medium  
- **Effort:** Low  
- **Source:** [docs/benchmark-philosophy.md](../../docs/benchmark-philosophy.md).

### Gap: `token_metrics.db` ↔ `RUN_DIR` join key

- **Current:** Two stores without a guaranteed foreign key.
- **Better approach:** UUID `run_uuid` created at run start; write into every `summary.json`, `aggregate.json`, and DB rows.
- **Impact:** Medium  
- **Effort:** Low–Medium  
- **Source:** Lineage / data-warehouse hygiene.

### Gap: RAG retrieval logging

- **Current:** RAG may influence the measured path; retrieval chunks may not be durably logged.
- **Better approach:** Persist **query + retrieved doc IDs + chunk hashes** (not necessarily full text) per knowledge phase for replay and leakage audits.
- **Impact:** High for “did the KB give the answer?” analysis  
- **Effort:** Medium (API + runner changes)  
- **Source:** RAG evaluation practice; shortcut detection themes in agent benchmarks.

### Gap: Threat model for agentic cluster access

- **Current:** `better_shell` blocks some patterns; no single **threat model** doc.
- **Better approach:** Document accepted risk: non-root cluster, namespace scope, command allow/deny philosophy, and what constitutes **out-of-benchmark** behavior (e.g. exfiltration attempts).
- **Impact:** Medium (safety + reproducibility when sharing logs)  
- **Effort:** Low (doc)  
- **Source:** Security engineering norm for autonomous agents.

### Gap: Ground-truth “oracle gap” tests

- **Current:** Manual review suggested for checks that pass without true fix.
- **Better approach:** Introduce **negative controls** (mutation tests): intentionally broken variants that **should fail** GT if checks are too weak; run in CI separate from model calls.
- **Impact:** High for long-term integrity  
- **Effort:** High  
- **Source:** Mutation testing / property-based testing analog for evaluators.

### Gap: Cross-platform comparability

- **Current:** Windows vs Unix shell differences affect tool success rates.
- **Better approach:** Record `platform` and shell; either **stratify results** by platform or **standardize** on one reference environment for published numbers.
- **Impact:** Medium  
- **Effort:** Low (record) / High (normalize env)  
- **Source:** Environment variance in integration testing literature.

### Gap: Embedder / knowledge pipeline lock for multi-model studies

- **Current:** Open question in taxonomy.
- **Better approach:** Treat **embedder + corpus version** as part of **harness version**; enforce constant embedder when comparing chat models unless the study explicitly varies retrieval.
- **Impact:** High for fair comparison  
- **Effort:** Medium  
- **Source:** Standardized scenario design (HELM-like).

### Gap: Retention, redaction, and sharing policy

- **Current:** Deferred in taxonomy.
- **Better approach:** Define **default redaction** for logs (tokens, kubeconfigs, Secret values), **retention TTL** for `.local/test_runs/`, and **export bundle** format safe for publication.
- **Impact:** Medium (compliance + collaboration)  
- **Effort:** Medium  
- **Source:** OTEL privacy posture; enterprise log hygiene.

---

## Additional enumerated concerns (not yet in taxonomy table)

1. **Shortcut and contamination detection:** Automated checks for “model read answer from fixture path,” “empty tool loop,” or “verification copied debug transcript.”
2. **Cost and budget telemetry:** Per-run dollar estimates with **hard caps** that fail closed with explicit `BUDGET_EXCEEDED`—distinct from hiding model incompetence.
3. **Clock skew and timeouts:** Document whether timeouts are wall-clock or CPU; record them in provenance for cross-machine comparison.
4. **Model API version pinning:** Provider models drift; store `openai_api_version` / provider response headers when available.
5. **Corpus / KB versioning:** If RAG corpus changes, benchmark results are not comparable—version the ingested corpus id in provenance.
6. **Human-in-the-loop contamination:** Procedures for runs assisted by humans (should be labeled `human_assisted: true`).
7. **Regression suite for the runner itself:** pytest covers code; add **golden-run** smoke (mock LLM or recorded transcript) to detect harness regressions independent of model quality.
8. **Adversarial prompts:** Whether benchmark prompts resist **prompt injection** from cluster content (e.g. malicious ConfigMap text)—relevant if measuring robustness.
9. **Accessibility of failure artifacts:** Ensure `ERROR` vs `TIMEOUT` vs `GROUND_TRUTH_FAIL` always produce **actionable** paths in `summary.json` for downstream tools.

---

## Top action items (priority order)

1. **Run provenance schema** — git + cluster + schema versions in every `RUN_DIR` (highest leverage for trust).  
2. **Join key** — `run_uuid` linking filesystem artifacts and `token_metrics.db`.  
3. **Verification report persistence** — durable middle-layer evidence.  
4. **Parallelism contract** — implement namespace/suffix strategy or enforce disjoint sets in preflight.  
5. **Verification temperature lint** — align configs with philosophy.  
6. **Reporting standard for stochastic runs** — document *n*, aggregation, and seeds in published results.  
7. **RAG retrieval fingerprint** — log query + doc ids/chunk hashes for audit.  
8. **Optional OTEL** — after A–7 stabilize the JSON contract.

---

## Disregard list (attractive but wrong for this benchmark)

| Idea | Why skip or reject |
| --- | --- |
| **Retry until pass** on agent or GT failures | Violates [docs/benchmark-philosophy.md](../../docs/benchmark-philosophy.md) (masking model failures). |
| **Auto-loosen ground truth** when a “good” model fails | Data corruption; fix checks or accept honest FAIL. |
| **Model-specific hint tuning** per test | Same. |
| **Using only verification LLM as “the score”** | Collapses the verification hierarchy. |
| **Logging full prompts/completions everywhere by default** | Conflicts with OTEL-style privacy guidance and risks secret leakage; use opt-in or hashed references. |
| **Heavy ML platform first** | Premature without a minimal provenance contract; adds ops burden and dashboard pressure. |
| **Quarantining flaky benchmark scenarios without fixing** | Unlike product CI, hiding flaky benchmark tests **shrinks** the measured domain unless explicitly documented as **excluded from headline metrics**. |

---

## Grouping: quick wins vs strategic vs nice-to-have

| Bucket | Items |
| --- | --- |
| **Quick wins** | `run_uuid`; verification report file; temperature lint; `platform` + `kubectl context` in run metadata; flaky register doc |
| **Strategic** | Provenance schema; parallel isolation design; RAG retrieval logging; negative-control / oracle-gap tests for GT |
| **Nice-to-have** | OTEL export; cost caps with explicit status; adversarial robustness scenarios |
| **Work to avoid** | Pass-rate-optimized retries; unscoped prompt/completion logging; collapsing GT and verification |

---

## Link to prior work

- Taxonomy (repo surfaces and pillars): [benchmark-refactor-taxonomy-2026-03-28.md](../improved-prompts/benchmark-refactor-taxonomy-2026-03-28.md)  
- Prompt + original brainstorm: [benchmark-refactor-map-2026-03-28.md](../improved-prompts/benchmark-refactor-map-2026-03-28.md)
