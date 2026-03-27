# Technical Debt Review Section

## Focus Areas

Identify accumulated technical debt that slows development velocity,
increases bug risk, or blocks future work. Focus on debt that has
measurable impact, not theoretical purity.

## What to Look For

### High-Impact Debt (Critical)
- Hardcoded values that should be configurable (environment-specific
  URLs, credentials, feature flags baked into code)
- Copy-pasted logic: substantial code blocks duplicated across 3+ files
  that should be a shared utility
- Missing error handling on critical paths (database operations, external
  API calls, file system operations that silently fail)
- Outdated dependencies with known breaking changes in newer versions
  that block upgrades of other dependencies

### Structural Debt (Warning)
- TODO/FIXME/HACK/XXX comments indicating known problems left unresolved
  (extract and assess each one)
- Workarounds for bugs in dependencies that have since been fixed
- Temporary solutions that became permanent (migration scripts still
  running, compatibility shims for retired versions)
- Over-engineering: abstraction layers, factories, or strategy patterns
  wrapping code that has never varied and shows no sign of needing to

### Maintenance Burden (Warning)
- Configuration drift: multiple config files with overlapping or
  contradictory settings
- Build system complexity: custom scripts doing what standard tooling
  could handle
- Inconsistent dependency versions across packages in a monorepo
- Manual processes that could be automated (deployment steps, data
  migrations, environment setup)

### Upgrade Blockers (Suggestion)
- Deprecated API usage that will break on next major version
- Language features from old versions when newer alternatives exist
  and the project targets a modern runtime
- Pinned dependencies preventing security patches
- Test infrastructure that is brittle or slow, discouraging test writing

## Assessment Framework

For each debt item, estimate:

| Dimension | Scale |
|-----------|-------|
| **Impact** | How much does this slow development? (high/medium/low) |
| **Effort** | How hard is the fix? (high/medium/low) |
| **Risk** | What breaks if we ignore it? (high/medium/low) |
| **Urgency** | Is there a deadline forcing action? (yes/no) |

Prioritize: high-impact + low-effort items first (quick wins), then
high-impact + high-risk items (strategic investments).

## What to Skip

- Debt that is actively being addressed (check recent commits/branches)
- Stylistic debt (covered by style section)
- Test debt (covered by tests section)
- Debt in code scheduled for removal or rewrite

## Severity Guide

| Severity | Criteria |
|----------|----------|
| Critical | Blocks upgrades, causes recurring bugs, or prevents feature work |
| Warning | Accumulating cost that will compound over quarters |
| Suggestion | Cleanup that would improve developer experience |
