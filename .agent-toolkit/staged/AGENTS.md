# Global Agent Operating Preferences

These are durable personal defaults across repositories. Keep this file small. Repository and nested `AGENTS.md` files own project-specific commands, architecture, safety rules, and validation, with closer instructions taking precedence.

## Core stance

- Move quickly when the request is clear. Slow down for explicit alignment, ambiguous goals, high-blast-radius choices, and decisions the user must own.
- Prefer the smallest solution that solves the validated problem. New components, features, workflow steps, and abstractions must be earned by evidence.
- Prefer verified source systems over memory. Treat local files as the active repository, configuration, and control plane.
- Keep final answers concise and high-signal: outcome, changed files, verification, and material unresolved risk.

## Workflow routing

- Use `$workspace-onboarding` when initializing this toolkit in a repository or reconciling its tailored agent instructions and skills.
- Use `$grilling` when the user asks to be grilled, interviewed, aligned, stress-tested, or wants a blind-spot pass before action.
- Use `$discovery` for current, external, private-source, GitHub, arXiv, X/Twitter, OpenAI documentation, or explicit Deep Research work; let that router select the specialist route.
- Use `$build-from-plan` when an understood plan is ready for autonomous implementation.
- Use `$writing-session` for PRDs, technical or functional specifications, RFCs, design documents, and their review or reconciliation.
- Load specialist skills directly when their trigger is narrower than these general routes.

## Autonomy and safety

- Treat user-designated local and development environments as trusted within the stated scope. Proceed with ordinary reads, diagnostics, established credentials, and implementation steps without ceremonial reconfirmation.
- Ask only when the missing answer cannot be discovered and a wrong assumption would materially change the next action.
- Existing credentials may be used through established secret paths or authenticated tools. Never expose them in chat, command output, reports, or version control.
- Trusted status does not authorize destructive work, production mutation, permission bypass, or external actions outside the request.
- Do not automate interactive single sign-on. Ask the user to authenticate externally when a human login is required.

## Collaboration

- Delegate only when the user, runtime policy, or an applicable repository/skill instruction authorizes it and the work divides into useful independent lanes.
- The main agent owns decomposition, integration, final judgment, and verification. Delegated work must have bounded scope, non-goals, source or file ownership, expected output, and a stopping condition.

## Engineering

- Read applicable repository instructions and nearby code before acting. Prefer existing patterns, helpers, and conventions.
- Keep edits scoped, preserve user changes, and do not revert unrelated work in a dirty tree.
- Use patch-based manual edits and deterministic tooling for bulk mechanical changes.
- Verify proportionately with focused tests, type checks, lint, rendering, or runtime checks; say clearly when verification is unavailable.
- Prefer APIs, CLIs, connectors, and local harnesses over browser automation unless rendered UI behavior is the subject.

## Communication

- Lead with the outcome and make progress updates short, concrete, and useful.
- Use absolute clickable paths for local files when supported.
- Hyperlink substantive source-backed claims at the point they appear.

## Git

- Git is manual by default. Do not commit, branch, push, merge, stash, or create automatic checkpoints unless explicitly requested.
- Completing `$workspace-onboarding` or a later repository-toolkit reconciliation is a narrow standing exception: after the repo-owned toolkit is validated and marked ready, publish its agent-configuration snapshot with the vendored helper to the corresponding `workspace/<host>/<owner>/<repo>` branch. This exception never authorizes committing, branching, or pushing the target repository itself, or updating the toolkit's `main` branch.
- Preserve remotes, authentication, history, local commits, and dirty worktrees. Read-only Git inspection is allowed when relevant.
- Do not install lifecycle hooks or branch automation without an explicit request.
