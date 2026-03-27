---
name: comprehend
description: >
  Deep repository discovery and comprehension workflow for Codex. Use when
  the user wants to understand a codebase, map architecture, onboard to a
  project, or trace how a system works end to end.
metadata:
  short-description: Build a mental model of a repo
---

# Repository Comprehension

Build a usable mental model of the repository before making claims about it.
Favor structure, entry points, and major flows over exhaustive file-by-file
reading unless the repo is small.

## Sizing

Estimate scale first with `rg --files` or equivalent:

| Size | File Count | Default Approach |
| --- | --- | --- |
| Small | under 50 | read nearly all relevant source files |
| Medium | 50-500 | read docs, manifests, entry points, and representative modules |
| Large | over 500 | map structure first, then trace the primary flow only |

State the size class and adjust depth accordingly.

## Reading Order

Read in this order unless the repo suggests otherwise:

1. `README.md`, `CLAUDE.md`, architecture docs, and runbooks
2. dependency manifests and configuration files
3. primary entry points and routing or dispatch code
4. shared abstractions, utilities, and types
5. representative feature modules

## Discovery Stages

### 1. Structural Survey

- map top-level folders and their purpose
- identify languages, frameworks, and build tooling
- note whether the repo is single-package or a workspace/monorepo

### 2. Dependency Mapping

- identify core framework dependencies
- identify storage, networking, auth, test, and tooling dependencies
- note internal packages or shared libraries

### 3. Entry Point Tracing

- find the main entry point or command surface
- trace initialization
- follow at least one representative request, job, or CLI flow end to end

### 4. Pattern Recognition

For medium and large repos, identify the dominant conventions:

- module layout
- config loading
- error handling
- service, handler, controller, or repository patterns
- testing strategy

### 5. Use Case Synthesis

Explain what the system does for its users or operators, not just how the code
is arranged.

## Tool Strategy

- prefer `rg --files` for file discovery
- prefer `rg -n` for symbols, handlers, routes, and entry points
- skip generated code, vendored dependencies, build output, and lockfile noise
- sample representative modules instead of reading repetitive files one by one

## Deliverable

Unless the user asked for a saved artifact, respond inline with:

- repository purpose
- technology stack
- component map
- traced data or control flow
- key patterns and design decisions
- modification starting points
- open questions or uncertainties

If the user wants persistent documentation, or the repo already maintains
architecture notes, write or update `docs/ARCHITECTURE.md`.

Use this section structure for a saved artifact:

```markdown
# [Repository Name] Architecture

## Purpose
## Technology Stack
## System Overview
## Component Map
## Data Flow
## Key Patterns
## Design Decisions
## Entry Points for Modification
## Open Questions
```

## Completion Check

Do not stop until you can answer these questions:

- What problem does this repo solve?
- Where does a request, job, or command enter the system?
- Which modules hold the important behavior?
- Where would you start to change feature X?
- What remains unclear from code alone?
