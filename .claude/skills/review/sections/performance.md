# Performance Review Section

## Focus Areas

Identify code patterns that cause unnecessary resource consumption, slow
response times, or scalability bottlenecks. Focus on algorithmic and
structural issues, not micro-optimizations.

## What to Look For

### Algorithmic Issues (Critical)
- O(n²) or worse loops that process collections (nested iterations over
  large datasets)
- N+1 query patterns: database queries inside loops
- Missing pagination on unbounded queries
- Recursive functions without depth limits or memoization
- Synchronous blocking in async contexts (blocking the event loop)

### Resource Management (Warning)
- Unclosed connections, file handles, or streams
- Missing connection pooling for databases, HTTP clients
- Unbounded caches or in-memory stores that grow without eviction
- Large file reads loaded entirely into memory instead of streaming
- Missing timeouts on network requests or database queries

### Data Access Patterns (Warning)
- SELECT * when only specific columns are needed
- Missing indexes implied by query patterns (WHERE, JOIN, ORDER BY)
- Repeated identical queries within a single request lifecycle
- Loading full objects when only IDs or counts are needed
- Missing eager loading causing waterfall queries

### Concurrency (Warning)
- Sequential execution of independent async operations (missing
  Promise.all, asyncio.gather, goroutine parallelism)
- Lock contention on shared resources
- Thread-unsafe access to shared mutable state
- Missing backpressure on queues or streams

### Build & Bundle (Suggestion)
- Importing entire libraries when only specific functions are needed
- Missing tree-shaking or dead code elimination
- Large assets not compressed or lazily loaded
- Missing code splitting for frontend bundles

## What to Skip

- Micro-optimizations (loop unrolling, bit shifting instead of division)
- Performance of code that runs once at startup
- Test code performance
- Hypothetical scale issues in code that handles known-small datasets

## Severity Guide

| Severity | Criteria |
|----------|----------|
| Critical | Causes visible latency, OOM, or timeout under normal load |
| Warning | Will degrade at scale or under load spikes |
| Suggestion | Optimization opportunity with measurable but non-urgent impact |
