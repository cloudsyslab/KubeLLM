# SARIF Summary Template

Format static analysis results for inclusion in worker prompts.

## Template

```markdown
## Static Analysis Context (from {tool_name})

**Total**: {total_count} findings
**By severity**: {error_count} errors, {warning_count} warnings, {info_count} info

### Findings Relevant to This Worker's Section

{For each finding matching this worker's section focus:}
- **{rule_id}** [{severity}]: `{file}:{line}` - {message}

### Worker Instructions

- These findings are machine-generated and may be false positives.
- If you confirm a tool finding, include it in your output with your own
  severity assessment and evidence.
- If you determine a tool finding is a false positive, note it as
  `TOOL-FP: {rule_id} at {file}:{line} - {reason}`.
- Do not re-scan for patterns the tool already covers. Focus on issues
  requiring human judgment.
```
