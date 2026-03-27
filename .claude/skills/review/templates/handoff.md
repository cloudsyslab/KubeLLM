# Actions Agent Handoff Format

This JSON structure is the contract between `/review` (producer) and
`/fixer` (consumer). The fixer agent should be able to implement fixes
using only this payload — no conversation context required.

## Schema

```json
{
  "review_id": "review-YYYY-MM-DD-{section}",
  "timestamp": "ISO-8601",
  "repository": "path/to/repo",
  "scope": {
    "section": "security | performance | architecture | style | debt | tests | full",
    "path": "optional/scoped/path or .",
    "depth": "small | medium | large"
  },
  "summary": {
    "total_findings": 0,
    "critical": 0,
    "warning": 0,
    "suggestion": 0,
    "files_examined": 0,
    "pre_verification_count": 0,
    "filter_rate": "0%"
  },
  "findings": [
    {
      "id": "SEC-001",
      "severity": "critical",
      "category": "security",
      "file": "src/auth/login.ts",
      "line": 42,
      "title": "SQL injection via unsanitized user input",
      "problem": "User-supplied email is interpolated directly into SQL query without parameterization.",
      "evidence": "const query = `SELECT * FROM users WHERE email = '${req.body.email}'`",
      "suggestion": "Use parameterized query: db.query('SELECT * FROM users WHERE email = $1', [req.body.email])",
      "impact": "Attacker can extract or modify any database record via crafted email input.",
      "confidence": 0.95,
      "verification": {
        "evidence_verified": true,
        "structure_confirmed": true,
        "line_corrected": null,
        "confidence_adjusted": 0.95
      },
      "context": {
        "callers": ["src/routes/auth.ts:15"],
        "dependencies": ["src/db/connection.ts"]
      }
    }
  ]
}
```

## Field Notes for Fixer Agent

- **id**: Use to reference findings in commit messages (e.g., "Fix SEC-001")
- **file + line**: Start point for the fix. May need to read surrounding context.
- **evidence**: The exact code to find and replace.
- **suggestion**: The fix direction. Fixer should verify it compiles/passes tests.
- **context.callers**: Other files that call this code — check for ripple effects.
- **context.dependencies**: Files this code depends on — may need coordinated changes.
- **confidence**: Lower confidence = fixer should verify more carefully before changing.

## Ordering

Findings are ordered by:
1. Severity (critical first)
2. File path (group related findings)
3. Line number (top-down within a file)
