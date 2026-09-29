# Cleanup-recovery continuation archive

This is a supplemental, privacy-filtered archive for the continuation of the stopped 270-attempt KnowledgeAgentOnly vs allStepsAtOnce comparison. It retains allowlisted case summaries, categorical KAO stage outcomes, run controls, effective model IDs, aggregate metrics, and derived timing/comparison tables. All run configs are named `run_config.archived.json` so the default analyzer excludes them.

Raw logs, prompts, plans, commands, free-form tool output, raw Ground Truth checks, service endpoints, and private lane details are omitted. The first 141 outcomes remain in [`../knowledgeagentonly-vs-allsteps-integrity-stop-2026-09/`](../knowledgeagentonly-vs-allsteps-integrity-stop-2026-09/); this supplement archives 108 additional results and records the later cleanup stop. See `campaign_status.json`, `integrity_event.json`, and `interim_analysis.md`.

The continuation stopped after 249/270 total results. AllStepsAtOnce rep 5 completed; KnowledgeAgentOnly rep 5 stopped at case 6 after the teardown postcondition found the configured image still present. No retry or manual cleanup was performed. The partial fifth KAO repetition is not a complete paired suite.
