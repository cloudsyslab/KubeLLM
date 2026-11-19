# Model Router v0 — 2026-11-19

This is the sanitized evidence pack for the first paired model-router experiment and its Responses output-cap follow-up.

- `paired_runs/`: 405 allowlisted run exports created with `scripts/archive_exploratory_run.py`.
- `campaign_summary.json`: aggregate paired DebugAgent outcomes and campaign integrity counts.
- `model_router_v0_registry.json`: the reviewed registry snapshot used to define candidates and rate priors.
- `router_waves/80_output_tokens/`: original 2,160-call router wave, preserving the 80-token condition.
- `router_waves/25000_output_tokens/`: separate 2,160-call follow-up with a 25,000-token Responses output limit and reasoning-token telemetry.
- `comparison.md` / `comparison.json`: cross-wave analysis, outcome agreement, validity, policy results, and interpretation.
- `figures/`: cross-wave validity and policy selection plots. Each wave also retains the router report figures.

Raw logs, API request identifiers, private lane configuration, prompts, and raw model outputs are not included. Ground Truth is the authoritative outcome; the one unknown candidate outcome is kept unknown.
