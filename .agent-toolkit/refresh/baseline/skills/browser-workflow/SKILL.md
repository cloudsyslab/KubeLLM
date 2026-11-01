---
name: browser-workflow
description: Use Codex's sidebar browser for website interaction and rendered QA, recover there, and report blockers before changing browser surfaces.
---

# Browser Workflow

Use this workflow when a task needs rendered website navigation or interaction, a local browser preview, or browser-based visual QA. It coordinates the browser surface; it does not replace APIs, CLIs, or connectors when those can provide the needed data directly.

## Keep browser work in the sidebar

- Use Codex's built-in sidebar `@Browser` as the default browser surface. Follow the current computer-use documentation, select the in-app-browser tab explicitly, and verify its identity and target URL before interacting. Do not infer that an ambient URL or an external Chrome tab is the selected surface.
- Keep navigation, page interaction, inspection, and browser recovery in that sidebar session. Preserve user tabs and session data.
- Do not switch to native Chrome, its extension, another browser provider, or a separately launched Playwright, CDP, Browser Use, screenshot, or capture harness unless the user explicitly chooses that runtime for the current task. A protocol or library name alone is not a surface choice; use it when it is a documented capability of the selected sidebar browser.
- Continue using API, CLI, and connector routes for source or data access when a rendered page is not needed.

## Recover and report

Classify the observed failure before retrying. Use only a supported, targeted recovery in the sidebar, such as reacquiring the current in-app tab, opening a fresh sidebar tab, or reloading after a specific transient error. Make one correction-based retry; stop after an equivalent failure recurs. Do not change browser settings, clear site data, transfer cookies, or bypass a provider or site restriction as recovery.

For an authentication challenge, have the user sign in directly in the sidebar session. Do not automate interactive sign-in or move authentication to another profile.

If the sidebar cannot provide the required page or evidence, report the exact surface, URL or state, error, recovery tried, and what remains unavailable. If another runtime could resolve it, explain what it would add and let the user choose whether to use it for this task. Do not silently continue through that runtime or claim the blocked check passed.
