# Legacy benchmark logs

These files were moved here from `debug_assistant_latest/result_logs/` and
`debug_assistant_latest/debug_logs/` so benchmark-related artifacts share the
`data/` root. Their original filenames and contents are preserved.

The text result dumps are in `result_logs/`; paired Knowledge Agent and Tools
Agent logs are in `agent_logs/`. They do not have the structured
`run_config.json` and per-case evidence required by the current analyzer.
Treat them as archival source material only. They are excluded from current
benchmark comparisons and must not be used to fill missing outcomes in the
structured exports.
