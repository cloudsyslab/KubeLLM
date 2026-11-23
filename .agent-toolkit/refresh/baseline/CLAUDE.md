@AGENTS.md

# Claude Code bindings

The instructions imported above and the skills in `.claude/skills/` are the
same files Codex uses, and they remain the authority. `.claude/skills` links to
`.agents/skills`; edit a skill at its `.agents/skills/` path, because Claude Code
does not write through the link.

Where those files name a Codex-only mechanism, read it as:

- **Codex as the acting agent**, as in "Codex's recommended answer": you.
- **`$skill` invocations:** `/skill` or `$skill` both count, including the
  fresh `$build-from-plan` and `$website-design-build` invocations that open
  their gates.
- **Managed worktrees:** use the host's managed worktree tool when available;
  otherwise use `git worktree` with the same branch and preservation rules.
- **Discovery's `gpt-6-luna` worker at `xhigh`:** a read-only Claude subagent
  given the same narrow lane, mutation limits, evidence packet, and stopping
  condition. If that subagent cannot be dispatched, stop and report it; do not
  research in the main agent instead.
- **Runtime-managed `$openai-docs` and `$deep-research`:** not available here.
  Route the request through Discovery's ordinary source-routed lane, official
  sources first, and say that the Codex specialist was not used.
- **Codex's sidebar `@Browser`:** Claude's built-in browser pane. Any other
  browser runtime still requires the user's explicit choice for the current
  task.

Everything else in `AGENTS.md` applies unchanged.
