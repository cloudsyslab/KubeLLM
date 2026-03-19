---
name: comprehend
description: >
  Deep repository discovery and comprehension skill that builds a complete
  mental model of a codebase equivalent to a senior founding engineer's
  understanding. Produces structured architecture documentation. Use when
  the user asks to understand a repository, map out functionality, learn
  how a codebase works, onboard to a project, or invokes /comprehend.
user-invocable: true
context: full
allowed-tools: Read, Glob, Grep, Bash, Write, Task
---

# Repository Comprehension Mode

Build a complete mental model of a codebase equivalent to a senior founding engineer's understanding. Output a structured architecture document.

---

## Scope

**In scope**:
- Architecture and component relationships
- Data flow through primary use cases
- Design patterns and conventions
- Build system and dependencies
- Key abstractions and their purposes
- Monorepo structure and inter-package relationships

**Out of scope**:
- Line-by-line code review
- Security auditing
- Performance optimization recommendations
- Generated code, vendored dependencies, build artifacts

**Stopping conditions**:
- Architecture document covers all major components
- Primary use cases are traceable end-to-end
- You can explain WHY the system is structured this way
- Further exploration yields diminishing insight

---

## Adaptive Sizing

Before beginning, assess repository scale:

| Size | File Count | Approach |
|------|------------|----------|
| Small | <50 files | Exhaustive: read all source files |
| Medium | 50-500 files | Sampled: read entry points, key modules, trace 2-3 flows |
| Large | 500+ files | Strategic: map structure, read READMEs/docs first, trace primary flow only |

State the size classification and your approach before proceeding.

---

## Discovery Stages

### Stage 1: Structural Survey (Always)

**Actions**:
1. List root directory contents
2. Identify config files (package.json, Cargo.toml, pyproject.toml, go.mod, etc.)
3. Read README.md if present
4. Map folder purposes from names and contents

**Output**: Directory tree with one-line annotations per folder.

**Gate**: Proceed when you can name the language/framework and primary entry point.

### Stage 1.5: Monorepo Detection (Always)

**Indicators**:
- `packages/`, `apps/`, `services/` folders
- Workspace configs: `pnpm-workspace.yaml`, `lerna.json`, `nx.json`
- Multiple `package.json` / `go.mod` / `Cargo.toml` files

**If monorepo detected**:
1. Map workspace structure
2. Identify shared packages vs applications/services
3. Document inter-package dependencies
4. Each package gets dedicated analysis

**Gate**: Proceed when workspace structure is mapped (or confirmed single-package).

### Stage 2: Dependency Mapping (Always)

**Actions**:
1. Parse dependency manifest(s)
2. Categorize: framework, database, HTTP, testing, utilities
3. Identify custom/internal packages

**Output**: Dependency table with purpose column.

**Gate**: Proceed when you understand what external systems this connects to.

### Stage 3: Entry Point Tracing (Always)

**Actions**:
1. Find main entry (main.ts, index.js, cmd/main.go, etc.)
2. Trace initialization sequence
3. Identify routing/dispatch mechanism
4. Read 1-2 representative handlers/endpoints end-to-end

**Output**: Sequence of initialization steps; one traced request flow.

**Gate**: Proceed when you can describe how a request enters and exits the system.

### Stage 4: Pattern Recognition (Medium/Large only)

**Actions**:
1. Grep for common patterns: Repository, Service, Controller, Handler, Model
2. Sample 2-3 instances of the dominant pattern
3. Identify error handling convention
4. Note configuration loading approach

**Output**: Pattern catalog with examples.

**Gate**: Proceed when you can predict where new code of type X would go.

### Stage 5: Use Case Synthesis (All sizes)

**Actions**:
1. Infer primary use cases from routes/commands/exports
2. Map actors (users, services, cron) to capabilities
3. Document 2-3 end-to-end workflows

**Output**: Use case list with actor and entry point.

**Gate**: Proceed when you can describe what this system DOES, not just what it IS.

### Stage 6: Mental Model Assembly (Always)

Synthesize discoveries into the output document.

---

## Tool Strategies

**File discovery**:
- Use Glob with patterns: `**/*.{ts,js,py,go,rs}` for source
- Exclude: `**/node_modules/**`, `**/vendor/**`, `**/*.min.*`, `**/dist/**`

**Targeted search**:
- Grep for: `export`, `class`, `def `, `func `, `router`, `handler`
- Find entry points: `main`, `index`, `app`, `server`

**Reading priority**:
1. README, ARCHITECTURE.md, docs/*.md
2. Config/manifest files
3. Entry points and routers
4. Shared utilities and types
5. Individual feature modules (sample, don't exhaust)

**File reading limits**:
- Small repos: No limit
- Medium repos: Max 30 files deep-read
- Large repos: Max 15 files deep-read; rely on structure + grep

---

## Output Format

Save to: `docs/ARCHITECTURE.md`

Required sections:

```markdown
# [Repository Name] Architecture

## Purpose
[One paragraph: what problem this solves, for whom]

## Technology Stack
[Language, framework, database, key dependencies]

## System Overview
[High-level description; optional ASCII diagram]

## Monorepo Structure (if applicable)
| Package | Type | Purpose |
|---------|------|---------|
| ... | app/lib/shared | ... |

## Component Map
| Component | Location | Responsibility |
|-----------|----------|----------------|
| ... | ... | ... |

## Data Flow
[Primary use case traced step-by-step]

## Key Patterns
[Architectural patterns, conventions, abstractions]

## Design Decisions
[Observed trade-offs and likely reasoning]

## Entry Points for Modification
| Goal | Start Here |
|------|------------|
| Add new API endpoint | ... |
| Modify data model | ... |
| Add new feature | ... |

## Open Questions
[Things unclear from code alone; would ask a human]
```

---

## Verification

Before declaring complete, confirm:
- [ ] Can explain the system's purpose in one sentence
- [ ] Can trace a request from entry to response
- [ ] Can predict where to add a new feature
- [ ] Have documented what's NOT clear
- [ ] Output document has all required sections

---

## Anti-Patterns to Avoid

- Reading every file in large repos (use sampling)
- Narrating each file as you read it (synthesize at the end)
- Stopping at WHAT without reaching WHY
- Ignoring test structure (reveals intended behavior)
- Missing generated/vendored code (wastes tokens)
