# Calibration Script

Adjusts per-rule confidence offsets from historical feedback.

## Prerequisite

`reviews/findings-ledger.jsonl` must have >= 20 resolved entries.

## Steps

### 1. Compute per-rule acceptance rates

```bash
cat reviews/findings-ledger.jsonl | \
  jq -r 'select(.outcome != "pending") | [.rule_pattern, .outcome] | @tsv' | \
  sort | uniq -c | sort -rn
```

- `acceptance_rate = (accepted + fixed) / total_resolved`
- `false_positive_rate = false_positive / total_resolved`

### 2. Compute confidence offsets

For each `rule_pattern` with >= 5 resolved entries:

```text
offset = acceptance_rate - 0.75
offset = clamp(offset, -0.2, 0.1)
```

### 3. Write calibration file

Save to `skills/review/calibration.json`:

```json
{
  "last_calibrated": "2026-03-25T10:30:00Z",
  "entries_analyzed": 150,
  "offsets": {
    "sql-injection-string-interpolation": 0.05,
    "n-plus-one-query-in-loop": -0.1
  }
}
```

### 4. Application

In Phase 3, after computing `confidence_adjusted`, apply:

```text
final_confidence = confidence_adjusted + calibration_offset[rule_pattern]
final_confidence = clamp(final_confidence, 0.5, 1.0)
```

If `final_confidence < 0.7`, drop the finding.
