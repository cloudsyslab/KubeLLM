# Browser recovery and QA

Use this reference for preview setup, a browser failure, and implementation verification inside the current authorized build pass. Diagnose the failing layer before changing tools or retrying. Verification completes that pass's deliverable; it does not authorize a later pass or mode transition.

## Establish an observable preview

1. Use [Browser Workflow](../../browser-workflow/SKILL.md) and the Codex sidebar `@Browser` for rendered inspection. Read its runtime documentation, verify the selected in-app tab, and use only documented controls. Do not assume viewport, screenshot, console, or evaluation capabilities.
2. Inspect the project's actual preview command and existing server. Start the appropriate app or a static HTTP server rooted only in the exploration artifact folder, using an available port and loopback binding where appropriate. Keep the process available while the user is reviewing.
3. Verify the intended URL responds and returns the expected page content. A server's startup message is insufficient. A local environment may isolate shell loopback access from the browser, so a failed `curl` alone does not establish that the server is down. Confirm through an available permitted health check or supported browser, then inspect server logs if readiness still fails.
4. Open the HTTP preview through the supported browser route. Check the rendered state, not just navigation success. Distinguish shell reachability from browser-provider reachability.

Use a localhost HTTP preview by default. `file://` is not a general recovery route: browser providers may reject it, and relative assets, modules, and fetch behavior can differ. Use it only when explicitly supported and adequate for the artifact; report its verification limits.

## Recover by layer

| Observed failure | Next useful check/action |
| --- | --- |
| Missing executable, package, or browser | Inspect installed runtimes, project scripts, and available provider tools. Use an existing supported route before requesting a new installation; do not trigger package/browser downloads merely to take a screenshot. |
| Local server cannot bind, permission denied, or sandbox error | Read the exact error and distinguish the requested bind from application failure. Use the environment's supported server mechanism. Do not weaken sandbox settings or permissions. |
| Dependency download or upstream request fails | Treat as a shell/network/toolchain issue. Inspect the error and available local assets/dependencies; a working browser does not prove shell network access. Keep a dependency-free design preview moving where it answers the question. |
| Shell HTTP check fails | Inspect server process/logs, host, port, requested path, and the shell's network permissions. A sandbox restriction can block shell loopback access while the browser can load the page. Confirm through a permitted health check or supported browser before diagnosing server startup. |
| Shell HTTP succeeds but browser cannot open | Inspect the sidebar provider error and supported local-preview mechanism. Check the exact URL and make a targeted sidebar recovery. If a different provider is needed, report why and let the user choose it for this task. |
| A previously working localhost URL reports connection refused | Check whether the preview process still owns the port. Restart the explicit preview helper, verify its HTTP 200 health check, then open a fresh browser tab at the URL. A stale browser connection-error page can no longer reload the original localhost URL correctly. |
| Page opens but assets/media/layout are missing | Inspect asset paths/loading and page state. For a saved reference, compare the live page, WACZ resource index, and offline replay; separate a missed capture or blocked network response from a general browser failure. |
| Screenshot exists but does not show the expected state | Inspect the image, viewport, scroll/state, and asset readiness. Capture the actual target state; nonempty file output does not establish fidelity. |

Retry in the sidebar when evidence supports a concrete correction. After two equivalent failures at one layer, stop repeating that route and report the blocker. Preserve the artifact and continue independent work. Never bypass a provider restriction, automate interactive authentication, or claim completed browser QA from code inspection. If another browser runtime is needed to verify the accepted goal, explain the gap and let the user choose whether to use it.

## Meaningful implementation checks

Choose checks for the changed surface rather than running an indiscriminate suite:

- Render the actual implemented page at desktop and mobile sizes; include a relevant intermediate width when layout behavior changes there. Record actual sizes. If the sidebar cannot set viewport dimensions, report the resulting coverage gap and ask the user before using a separate screenshot or browser harness; do not infer mobile quality from desktop rendering.
- Check hierarchy, line wrapping, overflowing content, spacing rhythm, cropped imagery, fixed/sticky elements, and asset/font loading. Compare against the accepted preview at similar sizes.
- Exercise changed navigation, calls to action, menus, forms, modal/tab/accordion states, and resulting destinations or visible feedback. Use local/test interactions within the authorized scope; live external form submissions are separate actions.
- For motion changes, play the source/live preview and the original replay at the recorded viewport/state when available. Check the trigger and relevant visible checkpoints, controls, keyboard/touch operation, and reduced-motion response. A still image alone does not verify motion; keep failed or missing archive/replay coverage labeled incomplete.
- Inspect keyboard focus and relevant reduced-motion behavior. Confirm touch-sized controls where responsive layout changes them.
- Check relevant console/network/server errors when supported. Name unavailable diagnostics as a gap rather than implying they passed.
- Run established build/type/lint checks proportional to the change. Add tests only when behavior needs regression protection; screenshots and direct interaction can be adequate for small reversible styling edits.

Before delivery, inspect screenshots yourself. Save or link meaningful desktop/mobile evidence and the exact page/interaction states checked. Keep the preview accessible for the user when practical, with its command or artifact location available for reopening. Report checks that passed separately from deferred or blocked checks.

If a full-page screenshot stretches a viewport-height hero or changes the layout being studied, use normal-viewport screenshots at the relevant scroll positions. Do not use a distorted full-page image as evidence of the original composition.
