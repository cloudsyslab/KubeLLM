# Style Review Section

## Focus Areas

Evaluate consistency of coding conventions, naming, formatting, and
patterns across the codebase. Focus on inconsistencies that cause
confusion, not personal preferences.

## What to Look For

### Naming Consistency (Warning)
- Mixed naming conventions within the same codebase (camelCase vs
  snake_case vs PascalCase used inconsistently for the same category)
- Misleading names: functions that don't do what their name suggests,
  boolean variables without is/has/should prefixes where the project
  uses them elsewhere
- Abbreviations used inconsistently (usr vs user, msg vs message)
- Generic names in non-generic contexts (data, info, temp, result as
  long-lived variables)

### Pattern Consistency (Warning)
- Error handling done differently across similar code paths (some throw,
  some return null, some use Result types)
- Async patterns mixed (callbacks, promises, async/await in the same
  layer)
- Import style inconsistency (default vs named, relative vs absolute)
- Configuration access patterns varying across modules

### Code Clarity (Suggestion)
- Complex boolean expressions without descriptive variable extraction
- Deeply nested conditionals (>3 levels) that could be flattened
- Magic numbers or strings without named constants
- Long functions (>50 LOC) that could be decomposed into clear steps
- Missing early returns that would reduce nesting

### Documentation Gaps (Suggestion)
- Public APIs without parameter/return documentation
- Complex algorithms without explanation of approach
- Non-obvious business rules implemented without context comments
- README outdated relative to current project structure

## What to Skip

- Formatting issues handled by automated formatters (prettier, black, gofmt)
- Personal style preferences not established as project conventions
- Documentation in internal/private code that is self-explanatory
- Test code style (unless it blocks test readability)

## Severity Guide

| Severity | Criteria |
|----------|----------|
| Warning | Inconsistency that causes real confusion or merge conflicts |
| Suggestion | Improvement that would make code more readable |

Note: Style findings are never "critical" — they do not break functionality.
