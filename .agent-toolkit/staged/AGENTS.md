# Global Agent Operating Preferences

These are durable personal defaults across repositories. Keep this file small. Repository and nested `AGENTS.md` files own project-specific commands, architecture, safety rules, and validation, with closer instructions taking precedence.

## Core stance

- Move quickly when the request is clear. Slow down for explicit alignment, ambiguous goals, high-blast-radius choices, and decisions the user must own.
- Prefer the smallest solution that solves the validated problem. New components, features, workflow steps, and abstractions must be earned by evidence.
- Prefer verified source systems over memory. Treat local files as the active repository, configuration, and control plane.
- Keep final answers concise and high-signal: outcome, changed files, verification, and material unresolved risk.

## Workflow routing

- Use `$workspace-onboarding` when initializing this toolkit in a repository or refreshing its tailored agent instructions and skills from upstream `main`. Refresh is explicit per target: reconcile the previously adopted base, latest upstream candidate, and live repository configuration; preserve repository context, then validate and append its workspace snapshot.
- Use `$grilling` when the user asks to be grilled, interviewed, aligned, stress-tested, or wants a blind-spot pass before action.
- Use `$show-me` when a concept needs a visual explanation or a learning artifact; it owns the artifact forms, the house style, and the shared workbench.
- Use `$learn` only when the user explicitly invokes it to learn a concept or topic; it teaches, has the user explain back, and probes, routing frontier questions through `$discovery`.
- Use `$discovery` for current, external, private-source, GitHub, arXiv, X/Twitter, OpenAI documentation, or explicit Deep Research work; let that router select the specialist route.
- Use `$cloudflare-cli` for Cloudflare administration and deployment. Prefer the project's Wrangler and the Cloudflare API with existing environment or Keychain credentials; reserve dashboard navigation for operations that require rendered interaction or human setup.
- Use `$browser-workflow` for website interaction, rendered previews, or browser QA. Keep those activities in Codex's sidebar `@Browser`; the user chooses explicitly before each task leaves that surface.
- Use `$build-from-plan` when an understood plan is ready for autonomous implementation. After every grilling pass, only the user's fresh, explicit invocation of that skill to execute the current plan permits execution. Agreement, earlier build permission, skill references, and agent-initiated loading do not count; a new grilling pass suspends execution and resets the gate.
- Use `$writing-session` for PRDs, technical or functional specifications, RFCs, design documents, and their review or reconciliation.
- Use `$build-from-plan` for the complete feature workline: create or resume its feature branch and linked worktree, implement and validate the plan, make coherent commits, push the verified personal repo or fork, and open or update its draft PR. Do not push to workplace or third-party repositories or directly to a default branch.
- Use `$reconcile-branches` after feature PRs are ready. Its fresh invocation owns integration, required checks, independent regression review, eligible merges in dependency order, and safe cleanup of completed worklines. It cannot bypass repository gates.
- Use `$publish-github` to polish a side project and stage it in a private GitHub repository. Public visibility always requires separate explicit approval.
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
- For rendered browser work, keep navigation, interaction, and recovery in the sidebar `@Browser`. Do not select an external browser, Chrome extension, separate harness, or capture app without the user's explicit choice for that task; report a sidebar blocker and let the user choose the next runtime.

## Communication

- Lead with the outcome and make progress updates short, concrete, and useful.
- Use absolute clickable paths for local files when supported.
- Hyperlink substantive source-backed claims at the point they appear.

## Git

- Git is manual by default outside the named workflows. A fresh `$build-from-plan` invocation authorizes scoped branch/worktree setup, commits, and draft-PR publication in the user's verified personal repository or fork; it does not authorize merging. A fresh `$reconcile-branches` invocation authorizes in-scope merges after their required checks and independent regression review pass.
- Start each new implementation workline in one feature branch and linked worktree; reuse both when continuing it. Keep the canonical checkout on the default branch when safe. Before cloning a repository, check for its canonical checkout and reuse it; do not make duplicate clones.
- Completing `$workspace-onboarding` or a later repository-toolkit reconciliation is a narrow standing exception: after the repo-owned toolkit is validated and marked ready, publish its agent-configuration snapshot with the vendored helper to the corresponding `workspace/<host>/<owner>/<repo>` branch. This exception never authorizes committing, branching, or pushing the target repository itself, or updating the toolkit's `main` branch.
- `$learn` remains a narrow exception: it commits only the files it wrote to the user's learning repository, on that repository's open `learn/*` branch. It never pushes or commits in any other repository. Keep learning checkpoints local unless the user explicitly promotes selected work through the normal feature workflow.
- Preserve remotes, authentication, history, local commits, and dirty worktrees. Read-only Git inspection is allowed when relevant.
- Do not install lifecycle hooks or branch automation without an explicit request.
