# Claude Code Status Line — Clean Markdown Notes

## Customize your status line

Configure a custom status bar at the bottom of Claude Code to monitor things like:

- context window usage
- session cost
- elapsed time
- git branch / repo state
- working directory
- session identity

The status line runs a shell command or script you define. Claude Code sends session data to that script as JSON on `stdin`, and whatever the script prints to `stdout` becomes the visible status line.

---

## Why use it

A custom status line is useful when you want to:

- monitor context window usage while you work
- track session cost
- distinguish between multiple active sessions
- always see git branch and repo state

---

## Setup options

### Option 1: Use `/statusline`

You can use the built-in command and describe what you want in natural language.

Example:

```text
/statusline show model name and context percentage with a progress bar
````

Claude Code can generate the script for you and update settings automatically.

---

### Option 2: Manual configuration

Add a `statusLine` entry to your Claude settings file.

Typical user settings path:

```text
~/.claude/settings.json
```

Basic structure:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh",
    "padding": 2
  }
}
```

Notes:

* `type` should be `"command"`
* `command` can point to a script or be an inline shell command
* `padding` is optional and adds horizontal spacing
* settings reload automatically, but visible changes show on the next interaction

---

## Disable the status line

You can disable it by:

* asking `/statusline` to remove or clear it
* deleting the `statusLine` field from `settings.json`

---

## Step-by-step manual build

### 1. Create a script

Create a script such as:

```text
~/.claude/statusline.sh
```

The script should:

* read JSON from `stdin`
* extract the values you care about
* print a short line of text

### 2. Make it executable

```bash
chmod +x ~/.claude/statusline.sh
```

### 3. Point Claude Code at it

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

---

## How status lines work

Claude Code runs your command and pipes JSON session data into it via `stdin`.

Your script:

1. reads the JSON input
2. extracts the needed fields
3. prints text to `stdout`

Claude Code shows that output in the status area.

### Update behavior

The status line updates after:

* each new assistant message
* permission mode changes
* vim mode toggles

Other behavior:

* updates are debounced
* if a new update happens while your script is still running, the old run is canceled
* the status line runs locally and does **not** consume API tokens
* it may temporarily hide during certain UI interactions

### Output capabilities

Your script can output:

* a single line
* multiple lines
* ANSI-colored text
* clickable links using OSC 8 sequences

---

## Available JSON data

Claude Code provides JSON fields like these to your status line script.

### Model

* `model.id`
* `model.display_name`

### Working directory / workspace

* `cwd`
* `workspace.current_dir`
* `workspace.project_dir`

### Cost and timing

* `cost.total_cost_usd`
* `cost.total_duration_ms`
* `cost.total_api_duration_ms`
* `cost.total_lines_added`
* `cost.total_lines_removed`

### Context window

* `context_window.total_input_tokens`
* `context_window.total_output_tokens`
* `context_window.context_window_size`
* `context_window.used_percentage`
* `context_window.remaining_percentage`
* `context_window.current_usage`

### Session / metadata

* `session_id`
* `transcript_path`
* `version`
* `output_style.name`

### Optional mode / agent / worktree data

* `vim.mode`
* `agent.name`
* `worktree.name`
* `worktree.path`
* `worktree.branch`
* `worktree.original_cwd`
* `worktree.original_branch`

### Extra flag

* `exceeds_200k_tokens`

---

## Fields that may be missing

Some fields may be absent entirely depending on session mode.

Examples:

* `vim` only appears when vim mode is enabled
* `agent` only appears when agent mode is configured
* `worktree` only appears in worktree sessions

Some fields may also be `null`, especially early in a session.

Examples:

* `context_window.current_usage`
* `context_window.used_percentage`
* `context_window.remaining_percentage`

Use fallback logic in your scripts.

---

## Context window field behavior

The docs describe two main ways to think about context usage:

### 1. Cumulative totals

These track totals across the session:

* `total_input_tokens`
* `total_output_tokens`

Good for:

* measuring total session consumption

### 2. Current usage

This reflects the most recent API call:

* `input_tokens`
* `output_tokens`
* `cache_creation_input_tokens`
* `cache_read_input_tokens`

Good for:

* current context state
* accurate percent usage

### Important detail

`used_percentage` is based on input-side tokens only:

* `input_tokens`
* `cache_creation_input_tokens`
* `cache_read_input_tokens`

It does **not** include `output_tokens`.

So if you calculate percentage yourself, match that logic.

---

## Example patterns the docs cover

### Context usage bar

Show:

* model name
* context percentage
* visual progress bar

Typical idea:

* use `context_window.used_percentage`
* build a small bar such as 10 blocks wide
* fill blocks based on usage

---

### Git status with colors

Show:

* current git branch
* staged file count
* modified file count

Typical idea:

* detect whether the current folder is a git repo
* read branch name
* count staged and modified changes
* color-code the indicators with ANSI escape sequences

---

### Cost and duration

Show:

* total cost in USD
* total elapsed session time

Typical idea:

* read `cost.total_cost_usd`
* read `cost.total_duration_ms`
* convert milliseconds to minutes and seconds

---

### Multiple lines

A script can print more than one line.

Useful pattern:

* line 1: model + directory + git branch
* line 2: context progress bar + cost + duration

The docs note that each `echo` / `print` becomes a separate row.

---

### Clickable links

You can create clickable links with OSC 8 escape sequences.

Example use case:

* show a clickable link to the current GitHub repo

Typical approach:

* get the git remote URL
* convert SSH-style URL to HTTPS
* wrap visible text in OSC 8 hyperlink sequences

Terminal support matters.

---

### Cache expensive operations

Because the status line script runs often, expensive commands can slow things down.

The docs specifically call out commands like:

* `git status`
* `git diff`

Recommended pattern:

* cache expensive results to a temp file
* refresh every few seconds, such as every 5 seconds
* use a stable cache filename

Important note:

* do **not** use per-process identifiers like `$$`, `os.getpid()`, or `process.pid` in the cache filename
* each run is a new process, so that would defeat caching

---

## Windows configuration

The docs say Claude Code runs status line commands through Git Bash on Windows.

Two common approaches:

### Run PowerShell through Git Bash

```json
{
  "statusLine": {
    "type": "command",
    "command": "powershell -NoProfile -File C:/Users/username/.claude/statusline.ps1"
  }
}
```

### Run a Bash script directly

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

---

## Tips

* test with mock JSON piped into the script
* keep output short so it does not wrap badly
* cache slow operations if you are using git-heavy logic
* community projects mentioned in the docs include:

  * `ccstatusline`
  * `starship-claude`

---

## Troubleshooting

### Status line not appearing

Check:

* the script is executable
* the script prints to `stdout`, not `stderr`
* the script works when run manually
* `disableAllHooks` is not set to `true`
* `claude --debug` for first-invocation exit code / stderr logging

The docs also suggest asking Claude to read your settings file and run the configured command directly to surface errors.

---

### Status line shows `--` or empty values

Possible reasons:

* fields may still be `null` early in the session
* your script does not handle missing values
* Claude Code may need a restart if values stay empty after several messages

Recommended fix:

* use fallbacks like `// 0` in `jq`
* add null-safe logic in Python / Node / PowerShell

---

### Context percentage looks wrong

The docs note:

* use `used_percentage` for the best approximation of current state
* total token fields are cumulative across the session
* `/context` output may differ slightly because it may be calculated at a different moment

---

### OSC 8 links are not clickable

Check:

* your terminal supports OSC 8 hyperlinks
* Terminal.app does not support them
* SSH / tmux may strip them depending on setup
* `printf '%b'` is often more reliable than `echo -e`

---

### Escape sequence glitches

Complex ANSI / OSC output can sometimes render poorly.

If that happens:

* simplify the script
* remove colors or hyperlink escapes
* prefer plain single-line output first

---

### Script errors or hangs

The docs warn:

* non-zero exit codes or no output can blank the status line
* slow scripts cause stale or delayed updates
* a slow script may be canceled if a newer update arrives

Recommended fix:

* keep scripts fast
* test them independently with mock input

---

### Notifications sharing the same row

The docs mention that system notifications may appear on the right side of the same status line row.

Examples include:

* MCP server errors
* auto-update notices
* token warnings
* verbose-mode token counter

On narrow terminals, these may truncate your status line.

---

## Minimal custom example you can build from

This is a simple Bash example in your own notes style:

```bash
#!/bin/bash

input=$(cat)
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
dir=$(echo "$input" | jq -r '.workspace.current_dir // ""')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')

echo "[$model] ${dir##*/} | ${pct}% ctx | \$${cost}"
```

Pair it with:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

---

## One-line takeaway

A Claude Code status line is just:

* a command you configure
* JSON fed in on `stdin`
* text printed out to `stdout`

That means you can make it as simple or as advanced as you want.

```

This markdown adaptation is based on the current Claude Code “Customize your status line” docs page, including setup, field definitions, examples, Windows notes, and troubleshooting. :contentReference[oaicite:1]{index=1}

I can also turn this into a **closer page-by-page markdown transcription with all sections expanded**, while still keeping it safe to paste into your notes.
::contentReference[oaicite:2]{index=2}
```

[1]: https://code.claude.com/docs/en/statusline "Customize your status line - Claude Code Docs"
