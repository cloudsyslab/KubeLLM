# Parser corrective smoke evidence

Sixteen single-case attempts: `wrong_port` and
`environment_variable_wrong_name`, each with `allStepsAtOnce`, `stepByStep`,
`singleAgent`, and `knowledgeAgentOnly`, before and after the parser correction.
These small smoke samples establish operational evidence, not technique quality.

| Source condition | Attempts | Recorded statuses | Source revision |
|---|---:|---|---|
| Pre-fix, dirty working tree | 8 | 6 PASS, 2 TIMEOUT | `37da7cb0959fbec32d457981d967d8aacaa7033b` |
| Post-fix, clean working tree | 8 | 8 PASS | `e2b66f9f8aa12b659baa765234649658bf1f2b73` |

The two historical TIMEOUT labels are retained exactly as recorded, not
rewritten to match the corrected `knowledge_output_invalid` failure handling.
The dirty flag means the earlier revision alone cannot reproduce those runs.
Each post-fix run passed Ground Truth; Verification was true for six and
unknown for the two single-agent runs. Do not infer verifier agreement from GT.

Effective model identifiers were Knowledge `gpt-5-mini`, Tools `gpt-5-nano`,
and Verification `gpt-5-nano`. A configured Tools model does not mean that role
ran in `knowledgeAgentOnly`; consult the separate phase metrics and execution
counts. No model overrides were applied for the clean post-fix smoke matrix.

Exports retain safe summary/aggregate metrics, categorical deterministic
execution stages/counts where emitted, reviewed role models and temperature,
and revision/dirty provenance. Raw transcripts, plans, commands, endpoint/lane
configuration, verifier prose, and free-form errors are deliberately absent.
No missing artifacts or outcomes are invented. Original artifacts are private.

To reproduce an outcome-only export from its original raw run, use:

```bash
python3 scripts/archive_exploratory_run.py <RAW_RUN> <NEW_ARCHIVE_RUN_DIR> \
  --model-id gpt-5-mini --model-id gpt-5-nano
```

Keep `run_config.archived.json` unchanged: it excludes these observations from
the canonical seven-export analysis.
