# KubeLLM development iteration loop

**Canonical runbook:** [`docs/agent-loop.md`](../../docs/agent-loop.md)

Follow that document end-to-end (preflight → run → read `summary.json` → `--diagnose-last` → fix → `python3 -m pytest tests/ -v` → re-run). Root [`CLAUDE.md`](../../CLAUDE.md) lists the doc map and quick commands.

This file exists so Claude Code can load a stable rule path under `.claude/rules/`; do not duplicate the full loop here — edit `docs/agent-loop.md` instead.
