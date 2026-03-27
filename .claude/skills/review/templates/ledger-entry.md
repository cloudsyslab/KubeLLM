# Findings Ledger Format

Stored as JSONL at `reviews/findings-ledger.jsonl`. Each line is one
finding with its outcome.

## Entry Schema

```json
{
  "review_id": "review-2026-03-25-security",
  "finding_id": "SEC-001",
  "timestamp": "2026-03-25T10:30:00Z",
  "category": "security",
  "severity": "critical",
  "rule_pattern": "sql-injection-string-interpolation",
  "file": "src/auth/login.ts",
  "line": 42,
  "confidence_original": 0.95,
  "confidence_adjusted": 0.95,
  "evidence_verified": true,
  "structure_confirmed": true,
  "outcome": "pending",
  "outcome_timestamp": null,
  "outcome_reason": null
}
```

## Outcome Values

| Outcome | Meaning | Set By |
|---------|---------|--------|
| `pending` | Not yet acted on | review skill (auto) |
| `accepted` | Developer confirmed, will fix | user or fixer |
| `fixed` | Fix implemented and verified | fixer agent |
| `dismissed` | Developer chose not to fix | user |
| `false-positive` | Finding was incorrect | user or verification |

## Rule Pattern

Normalized string describing the finding type (for example,
`sql-injection-string-interpolation`,
`n-plus-one-query-in-loop`).

Enables aggregation across reviews.
