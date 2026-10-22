# Website design work handoff

Shared contract for `$website-design` and `$website-design-build`. Reading this reference from either skill does not invoke the other mode.

## Keep one recoverable design record

Use the site's existing design-note location. If none exists, use `design-exploration/<site>/design-work.md`. Prefer one short living record with prior pass summaries and linked evidence over a new document hierarchy. For a tiny approved fix, a compact paragraph containing the same decisions is enough. Do not create notes in an unrelated site or overwrite its existing decisions.

The saved record is the operational source for handoff between models and chats; the user's latest trusted steering takes precedence. Preserve important prior choices and name superseded decisions rather than allowing stale packets to override new input. Include enough context to resume without the original conversation. Link substantial captures, code, briefs, and previews instead of copying them into the record.

Keep these meanings separate:

| State | Meaning | Next authorized action |
| --- | --- | --- |
| `draft` | A consequential choice remains open | Continue the already-invoked reasoning mode |
| `ready` | The next brief is understood and agreed | Wait for an explicit `$website-design-build` invocation |
| `running` | The user explicitly started this pass | Execute or resume that same pass within scope |
| `review-ready` | Deliverables and verification are returned | Wait for an explicit `$website-design` invocation to review |
| `blocked` | A material decision or capability gap stops the agreed work | Return progress, evidence, and the decision needed; wait at the gate |

A saved state is context, not permission to auto-start a mode. Record the trusted start instruction when a pass begins so its scope is clear; that historical instruction is not transferable authorization for a later pass or a different chat. In a new chat, the user's explicit invocation plus the current agreed record establishes the next action.

## Minimal next-pass brief

Capture these fields in plain Markdown, using existing notes where they already establish the answer:

```markdown
# <Site> design work

## Intent and decisions
- Audience, visitor task, primary action, and desired visual character:
- Approved composition/components, motion, and product behavior:
- Protected copy, claims, assets, constraints, and deferred choices:
- Decision and evidence pointers:

## Current pass: <short identifier>
- State: draft / ready / running / review-ready / blocked
- Pass: references-discovery / direction-room / refinement / implementation
- Objective and deliverables:
- Scope: files/surfaces included and excluded:
- Creative latitude: what may be explored or tuned; what needs a decision:
- Sources and assets: exact URLs, pack paths, preview paths, and status:
- Success criteria and required browser/technical verification:
- Stop point and next user decision:
- Start instruction: record only after explicit invocation:

## Return from this pass
- Deliverables and usable preview/artifact links:
- Checks and observed results, with viewport/interaction states:
- Capture/replay/fidelity gaps and accepted adaptations:
- Material deviations, blockers, and recommended options:
- Remaining work and next mode trigger:
```

Do not fill unknown fields with invented facts. Include only details that help perform or assess this pass. Capture status must distinguish observation, recording, archive integrity/receipt, replay-tested behavior, visual comparison, and adaptation; a checksum or working video alone does not establish 1:1 interactive reproduction.

## Mode transitions

Agreement and mode entry are separate. “Yes,” “sgtm,” direction selection, a generic plan approval, or a record becoming `ready` does not begin execution. Enter either website mode only through the user's explicit invocation of its skill to use it. When grilling shaped the current plan, also require the user's fresh `$build-from-plan` invocation; it may accompany `$website-design-build` in the same request. Quoted examples, attached evidence mentioning a skill, and instructions emitted by an agent are not user mode triggers.

An invoked skill remains active through ordinary replies, corrections, and continuation of the same pass; do not ask for a new invocation on every message. Completion or a material blocker ends the work pass at a gate. Preserve the finished output and handoff, then let the user select a model and explicitly invoke the next skill. Neither skill changes the model automatically.

The gates apply to this paired website workflow. Supporting `$grilling`, `$discovery`, `$site-reference`, or `$build-from-plan` can supply methods inside an authorized mode when available; they do not implicitly enter the other website mode or authorize later stages. Do not change those generic skills to enforce website-specific behavior.
