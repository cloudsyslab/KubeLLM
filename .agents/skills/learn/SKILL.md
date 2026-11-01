---
name: learn
description: "Conversational learning through a teach, explain-back, and probe loop. Quick concept passes by default; deeper sessions build a living topic map, route frontier questions through discovery, and close with the user's own position. Keeps a personal git-tracked learning record and an approved learner profile. Invoke explicitly; ordinary questions are not learning passes."
---

# Learn

## Purpose

Help the user understand something by teaching and testing it, not by answering it. Lead with short teaching, then make the user explain it back and probe the weakest point of that explanation. Each pass leaves a small record in the user's learning repository, and an approved learner profile shapes how later passes teach. This skill never writes or commits in the user's other repositories.

## Explicit mode boundary

Enter this mode only when the user explicitly invokes `$learn`. A quoted skill name or a link discussed as a reference is not a trigger. Stay in the mode for the conversation without a fresh invocation per answer, until the user ends it or redirects to other work.

"Just tell me" means answer plainly and skip the loop for that turn.

## Learning home

Use `$LEARNING_HOME` when set, otherwise `~/learning`:

```text
<learning home>/
├── log.md            # one line per concept learned
├── profile.md        # approved learner preferences
└── <topic-slug>/
    ├── map.html      # living topic map (sessions only)
    ├── blog.html     # the session's closing write-up
    ├── kept/         # artifacts the user said they liked
    └── demos/        # sandboxed runnable demos
```

If it does not exist, ask once whether to create it as a local git repository. Never create a remote on your own. Follow the user's normal manual-Git policy: do not create the learning repository, branch, or commits without an explicit request.

At the start of every pass, read `profile.md` completely and scan `log.md` and any existing topic map. Build on what the user has already covered instead of re-teaching it.

## Modes

Infer the mode from the request. Do not offer a menu.

- **Quick pass** (default, for "what is X" or "explain Y"): teach about one screen with one visual, ask for an explain-back, run one probe, patch the gap, and record it. No map or demo. This usually takes three to five turns.
- **Session** (for "teach me the frontier of X", or "go deeper" during a quick pass): calibrate, build the topic map at the start, follow the user's tangents concept by concept with one interactive visual each, offer demos where running something would teach better than explaining it, and close with the user's position. "Go deeper" seeds the map from what the quick pass covered.

## The loop

1. **Teach.** Lead with an analogy or concrete example, then the mechanism, with one visual chosen as described in [Visuals and artifacts](#visuals-and-artifacts).
2. **Explain back.** Ask the user to explain it in their own plain words.
3. **Probe.** Ask one question aimed at the weakest point of their explanation. Use its mechanism ("why does that work?"), boundary ("what breaks it?"), contrast ("how is it different from X?"), or application ("where would you use it?"). Withhold your own answer until they attempt it. "idk" or "skip" reveals it immediately.
4. **Reveal and patch.** Put your answer beside theirs, name the gap precisely, and re-teach only that gap.

Repeat until a probe finds no material gap or the user moves on. Ask one question per turn. The user may skip any beat.

## At the edge of known material

When a question needs current, frontier, source-specific, or private evidence, or when your own knowledge is uncertain:

1. Say what you know and where it stops.
2. State the research question in one line. The user may redirect it.
3. Route it through `$discovery` and follow its delegation contract. Where the runtime supports background workers, dispatch the research in the background and ask the user to predict what it will find. Otherwise say the research is blocking and wait.
4. Teach from the returned evidence with citations, and compare it against the user's prediction.

Do not offer an unverified guess as the answer while research is pending. On the map, distinguish an **unsettled** edge (the field itself disagrees or lacks evidence) from a **researched** one (unknown to you before, now sourced).

## Session

- **Calibrate** with one question about what the user already thinks, unless the request, log, or profile already shows it.
- **Map, at the start.** As soon as the session begins, load `$show-me` with its building and interactive-visual guides, and create `<topic>/map.html` from its `map` layout (`artifact.py new … --layout map`), which draws the territory tree from the branch sidebar. Build it while the first research runs, or right after calibrating when there is none, so the map exists before the first reveal. Include:
  - the territory: one sidebar branch per question or tangent, sub-branches marked `sub`, in the order the user reached them;
  - sources per branch;
  - marked unsettled and researched edges;
  - open questions;
  - links to the blog, kept artifacts, and demos;
  - a **Current position** section.

  Update the map at every concept boundary and at the close, not every turn. Open it in the sidebar browser when inspection helps.
- **Concept boundary.** A concept ends when its probe finds no material gap or the user moves on. Before the first question of the next concept, finish the checklist: the concept has its interactive visual (or its in-chat sketch, for a pure definition), the map shows it, and its log line is appended. Never defer this to a later concept or a later turn.
- **Tangents.** Each tangent becomes a branch. A tangent far from the topic becomes a new topic folder.
- **Close.** Ask for the user's position, grill it with one or two probes against the evidence, write the final position into the map, and name where the frontier leads next. Then write `<topic>/blog.html` from `$show-me`'s `blog` layout: the session's argument and the user's position, readable cold by someone who was not there.

## Visuals and artifacts

`$show-me` owns how artifacts are made, including its house style and workbench; this skill decides which one fits the moment:

- **Quick pass:** in-chat sketches. Make one small interactive visual only when the concept is about motion, flow, or a parameter that a static picture would hide.
- **Session:** exactly one interactive visual per concept, made at the step that teaches or reveals it, and a blog at the close. Skip the visual only for a concept that is a pure definition, and use an in-chat sketch instead. These are required, so `$show-me`'s offer-first rule does not apply; by the close, the session has one map, one blog, and one interactive visual per concept.
- **Games and experiences:** when intuition or practice is the goal, offer one in a single line ("want to play this as a game?") and build it only on a yes. Paste an experience's exported results back into the conversation as evidence for the next probe.

Artifacts are temporary by default. When the user says they like one, keep it: a single file at `<topic>/kept/<name>.html`, or a workbench build at `<topic>/kept/<name>/` with its `src/` beside `<name>.html`. Use `_inbox/kept/` for a quick pass without a topic. Link kept artifacts from the map and the log line. Do not ask after every artifact.

## Demos

Demos are opt-in and belong to sessions. Keep each one in `<topic>/demos/<name>/`: local, self-contained, and with any Python environment inside the demo folder. Ask before installing a package, using an API key, or calling a paid or external service. Never modify the user's project repositories or global tooling.

When a demo shows something worth applying to the user's real workflows, close with a short application plan and hand it to `$grilling`. Real changes wait for the user's `$build-from-plan` invocation.

## Learner profile

`profile.md` holds approved, generalizable preferences about how the user learns: teaching style, analogies that land, useful visual forms, probe types, and pacing. It never holds covered concepts (the log owns those), session history, or project facts.

- Infer candidates from what worked or fell flat. Propose them as one short batch at a session's close, or at the end of a quick pass when the signal is strong, with one approval question.
- Write only what the user approves. Replace or remove superseded preferences instead of appending contradictions. Keep the file compact.
- The profile shapes teaching. It never overrides accuracy or safety.

## Record and finish

At the end of each quick pass, and at each concept boundary and close of a session:

1. Append one line per concept to `log.md`: `- YYYY-MM-DD · <concept> · <topic or —> · <links>`. The links point to the map, blog, kept artifacts, or demos. Do not add grades or levels; the artifacts speak for themselves.
2. Leave the learning files ready for review. Create repositories, branches, commits, or pushes only when the user explicitly requests that Git action.

If the learning home is not a git repository, keep the files there and say so once. Never push learning notes or open a PR automatically.
