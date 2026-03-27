# Architecture Review Section

## Focus Areas

Evaluate the structural health of the codebase: coupling, cohesion,
dependency direction, dead code, and drift from stated or implied
architectural patterns.

## What to Look For

### Coupling & Cohesion (Critical)
- Circular dependencies between modules or packages
- God objects/files: single files with excessive responsibility (>500 LOC
  of logic, many unrelated functions)
- Shotgun surgery indicators: changing one feature requires touching 5+
  unrelated files
- Feature envy: functions that use more from other modules than their own
- Inappropriate intimacy: modules reaching into another module's internals
  instead of using its public API

### Architectural Drift (Warning)
- Layer violations: UI code calling database directly, business logic in
  controllers, data access in presentation
- Inconsistent patterns: some modules use repository pattern, others query
  directly; some use dependency injection, others instantiate directly
- Abandoned abstractions: interfaces with single implementations that add
  complexity without value
- Convention violations: modules that break the project's own established
  patterns without clear reason

### Dead Code & Waste (Warning)
- Unreachable code paths (functions never called, branches never taken)
- Commented-out code blocks (should be deleted, not commented)
- Unused imports, variables, parameters, or return values
- Feature flags that are permanently on or off
- Deprecated code without removal timeline

### Dependency Health (Suggestion)
- Dependency direction violations (lower layers importing higher layers)
- Unnecessary abstractions adding indirection without flexibility
- Missing abstraction boundaries where implementation details leak
- Overly deep inheritance hierarchies (>3 levels)

### Module Organization (Suggestion)
- Files in wrong directories based on their responsibility
- Inconsistent naming conventions across similar modules
- Missing or misleading directory structure
- Configuration scattered across many locations

## What to Skip

- Architecture decisions that are clearly intentional and documented
- Small files that naturally have single responsibilities
- Framework-imposed patterns (even if they seem wrong, they may be required)
- Test organization (covered by tests section)

## Severity Guide

| Severity | Criteria |
|----------|----------|
| Critical | Circular dependencies, god objects blocking team velocity |
| Warning | Drift that will compound over time, dead code causing confusion |
| Suggestion | Organizational improvements that would clarify intent |
