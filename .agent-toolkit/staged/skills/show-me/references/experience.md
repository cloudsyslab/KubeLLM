# Experience

Put the user in a role, with real material and real judgment calls, such as "You are the LLM judge: grade these ten transcripts" or "You are on call: triage these alerts." Build it in the workbench when it has several steps (see [building.md](building.md)). An experience of five items or fewer, with simple choices, fits a single file.

## When

Use an experience for workflows, judgment, calibration, applying a rubric, or understanding a process from the inside, and only when the user wants one.

## Structure

1. **Briefing,** one screen at most:
   - the role;
   - the goal;
   - the constraints;
   - what "good" looks like.
2. **Material:** five to twelve items, real or realistic, drawn from the conversation's sources or the user's own data with their consent. Label synthetic items as synthetic.
3. **Decisions.** For each item, one constrained action (score, choose, sort, or flag), plus an optional one-line rationale.
4. **Reveal,** per item or at the end: the reference answer, expert judgment, or what actually happened, with the reasoning.
5. **Debrief:**
   - calibration: agreement rate, plus where and why the user diverged;
   - the underlying principle;
   - one question that transfers it to the user's own work.

## Rules

- **Specific material.** Use true-to-life items, not fluffy hypotheticals. Each decision should take under a minute.
- **Visible progress.** Show progress and allow going back. Save progress with the kit's `saved` so a reload does not lose work.
- **Exportable results.** End with a copy-as-text button that exports the user's decisions and the reference answers, so they can paste them into the conversation. That is how the calling workflow learns from the result.

## Build

Use the same steps as a game:

1. `workbench new`;
2. edit with `dev` running;
3. `build` into the topic's `kept/` folder;
4. check it before showing.

`Tabs` and `Dialog` from `@/ui` suit briefings and per-item detail.

## Common misses

- No reference answers.
- Too many items.
- Material too generic to require judgment.
- Results that never leave the browser.
