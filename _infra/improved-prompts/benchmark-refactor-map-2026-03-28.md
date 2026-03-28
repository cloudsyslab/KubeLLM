# Benchmark refactor mapping — prompt archive

Date: 2026-03-28

## Original input (brainstorm)

I want to do a large scale refactor based off of the benchmark philosophy I've developed - basically we're focusing on three core tasks, 1. Test Integrity, can a test create the require the correct conditions to benchmark model performance? Can the model execute the tools, etc have the CAPABILITY to successfully solve the conditions? 2. Data Logging, can we effectively log the data required to prove that benchmark? What initial conditions were, what reasoning looked like (for diagnosis), what end results were? Verifying if the agents hallucinated, and verifying true ground truth conditions if the test succeeded or not determinstically? 3. How can we launch more tests for more data at scale? How can I queue 10 different tests, how can I queue 10 different types of tests from different test cases? How can I queue 100? How can I queue 100 with different configurations? (this model, that model, etc)

There are probably more things we should be solving for, and thinking about when engaging with this repository, can you help me map them all out?

## Final prompt (agent-executable)

## Role and mission

You are a **senior benchmark architect** working inside the KubeLLM repository. KubeLLM is a **measurement instrument** for how well an LLM diagnoses and fixes real Kubernetes issues — not a product to maximize pass rate. Your job is to produce an **exhaustive, honest taxonomy** of concerns, gaps, risks, and dependencies for a **large-scale refactor** of benchmark infrastructure, organized around three pillars the team cares about, **plus** any additional dimensions the repo implicitly needs.

Read first (cite paths when you reference rules): `docs/benchmark-philosophy.md`, `docs/agent-loop.md`, and `docs/operations.md`.

## Non-negotiable constraints

- **Measurement fidelity over scores**: Never frame success as “more models pass.” Frame success as clearer capability signal, reproducibility, and auditable evidence.
- **Verification hierarchy** (highest to lowest authority): deterministic **Ground Truth** → independent **Verification Agent** → **Debug Agent self-report** (record only; never final truth).
- **Symptom-only test prompts**: Tests describe observed failure like a user bug report; they must not embed root cause, fix, or answer-adjacent hints.
- **Reproducibility**: Every test must be recreatable from fixtures and setup; no hidden cross-test state.
- **Breadth over roadmap**: Your primary output is a **taxonomy** (categories, sub-items, gaps). Do **not** spend the bulk of the response on implementation sequencing unless asked separately.

## Three pillars (expand each into a structured taxonomy)

### Pillar 1 — Test integrity

For each sub-bullet, state: **what “good” looks like**, **what can go wrong**, **what evidence would prove integrity**, and **which repo surfaces touch it** (e.g. `config_step.json`, setup/teardown, ground-truth commands, agent prompts).

- **Condition correctness**: Can the test **create** the intended broken state from scratch? Is that state **stable** for the duration of a run?
- **Observability of the task**: Does the symptom description match what a competent SRE would see? Any leakage of the solution into prompts or fixtures?
- **Capability vs difficulty**: Does the test discriminate real troubleshooting skill, or is it trivial/impossible for reasons unrelated to the skill being measured?
- **Tooling and permissions**: Can the model **actually** use the intended tools (kubectl, file access, RAG) under the runner’s environment? Any platform or sandbox gaps that confound measurement?
- **Evaluator soundness**: Do ground-truth checks prove the **specific fix**, not generic health? Can they pass without the intended remediation?

### Pillar 2 — Data logging and auditability

Produce a taxonomy of **what to log**, **when**, **at what granularity**, and **how it supports post-hoc analysis**.

Minimum dimensions to cover:

- **Initial conditions**: Cluster context, images, versions, fixture hashes or paths, seed/configuration of the run.
- **Intermediate reasoning artifacts**: Tool calls, command transcripts, RAG queries/retrievals (if available), model outputs — sufficient to diagnose *why* a path was taken without trusting self-reported success.
- **Terminal state**: Final cluster snapshots or command outputs needed to reconcile Ground Truth vs Verification Agent vs model claims.
- **Hallucination and overclaim detection**: What signals distinguish “claimed fix” from “verified fix”? What must be logged to audit that gap?
- **Determinism and ground truth**: What is **deterministically** checkable vs **model-judged**? How do logs preserve that distinction for later analysis?

### Pillar 3 — Local scale (now) and scale expansion (deferred)

**Now (local / single machine):**

- How to **queue many tests** (same machine): naming, ordering, parallelism limits, isolation between runs, artifact collision, failure propagation.
- How to **sweep configurations** locally (e.g. model id, temperature, API base URL): what must be parameterized, what must stay fixed for comparability, and how runs remain reproducible.

**Deferred (explicit subsection, do not implement):**

- List the **expansion surface area** for later: CI matrix runs, remote runners, quotas/cost, artifact retention, multi-tenant isolation, and any benchmark-philosophy risks (e.g. tuning for pass rate at volume).

## Additional dimensions (required)

Beyond the three pillars, enumerate **other refactor dimensions** this repository must solve for when treated as a serious benchmark. Examples of *classes* to consider (fill with repo-specific items, not generic platitudes):

- **Versioning** of prompts, evaluators, and fixtures so historical runs remain interpretable.
- **Failure taxonomy** for the runner (preflight, setup, agent, verification, teardown) and how failures should be recorded.
- **Documentation and operator ergonomics** so humans do not accidentally corrupt measurement.

## Output format (strict)

1. **Executive summary** (8–12 sentences): what the benchmark is measuring and why these pillars matter.
2. **Pillar 1 taxonomy** — nested bullets with the four fields per major item: good / failure modes / evidence / repo surfaces.
3. **Pillar 2 taxonomy** — same structure.
4. **Pillar 3** — “Local scale” taxonomy + **“Scale expansion (deferred)”** as a separate labeled subsection (bullet list of future concerns only).
5. **Additional dimensions** — table or nested list: **Dimension | Why it matters for measurement | Current gap | Suggested evidence or artifact**.
6. **Cross-cutting risks** — conflicts between pillars (e.g. logging volume vs reproducibility; parallelism vs isolation).
7. **Open questions** — only questions that **require human judgment** or **empirical measurement**; do not restate obvious doc quotes.

## Anti-patterns (explicit)

- Do not propose changes whose primary effect is higher pass rates without improving measurement accuracy.
- Do not collapse Verification Agent and Ground Truth into one notion of “the test passed.”
- Do not recommend logging or features that embed solution hints into prompts or traces visible to the model under test.

## Query

Using the repository as ground truth, produce the structured output above. When you reference behavior, tie it to **specific files or commands** you inspected (e.g. `python3 debug_assistant_latest/runner.py --list`).

---

## Executed output

The taxonomy produced by running this prompt against the repo is saved as:

- [`benchmark-refactor-taxonomy-2026-03-28.md`](benchmark-refactor-taxonomy-2026-03-28.md)
