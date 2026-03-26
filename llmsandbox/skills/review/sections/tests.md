# Test Review Section

## Focus Areas

Assess test coverage quality, test reliability, and testing strategy.
Focus on whether tests actually catch bugs, not just whether they exist.

## What to Look For

### Coverage Gaps (Critical)
- Critical business logic with no test coverage (payment processing,
  authentication, authorization, data validation)
- Error paths untested: only happy-path tests exist for functions with
  multiple failure modes
- Edge cases missing: empty inputs, null values, boundary conditions,
  concurrent access
- Integration points untested: database queries, API calls, file
  operations tested only with mocks that may diverge from reality

### Test Quality (Warning)
- Tests that always pass: assertions on constants, mocked returns tested
  against the same mock values, tautological tests
- Tests that test implementation, not behavior: breaking on any refactor
  even when behavior is preserved
- Overly broad assertions: checking entire objects when only one field
  matters, making tests fragile to unrelated changes
- Missing assertions: test functions that set up state but never assert
  anything (silently pass regardless of behavior)
- Flaky tests: tests with timing dependencies, external service calls,
  or shared mutable state that cause intermittent failures

### Testing Strategy (Warning)
- Testing pyramid inversion: more integration/E2E tests than unit tests
  (slow, brittle, expensive)
- Excessive mocking: so many mocks that the test no longer validates
  real behavior
- No integration tests at all: only unit tests with mocks, missing the
  actual system behavior
- Missing contract tests for service boundaries
- No test for the main entry point or primary user flow

### Test Infrastructure (Suggestion)
- Slow test suite: individual tests taking >1s, full suite >5min
- Test setup duplication: same fixture/helper code copied across test
  files instead of shared
- Missing test utilities for common patterns (factory functions, builders,
  custom assertions)
- Tests not running in CI or not blocking merges
- Outdated test dependencies or deprecated test framework usage

## Assessment Method

For coverage analysis:
1. Identify the critical paths (entry points, business logic, data access)
2. Search for corresponding test files
3. Check whether tests cover success, failure, and edge cases
4. Assess whether mocks accurately represent real dependencies

Do NOT rely solely on coverage percentage metrics — 90% coverage with
poor assertions is worse than 60% coverage with strong assertions.

## What to Skip

- Test file naming conventions (covered by style section)
- Test performance optimization (unless tests are too slow to run)
- Snapshot test maintenance (unless snapshots are clearly stale)
- E2E test infrastructure setup details

## Severity Guide

| Severity | Criteria |
|----------|----------|
| Critical | Critical business logic has zero test coverage |
| Warning | Tests exist but are weak, flaky, or test the wrong thing |
| Suggestion | Test infrastructure or strategy improvement |
