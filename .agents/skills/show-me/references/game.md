# Game

Build intuition by doing. The mechanic is the concept, so winning requires understanding it. Built in the workbench (see [building.md](building.md)).

## When

Use a game for decisions under tradeoffs, estimation, timing, prioritization, or pattern recognition, and only when the user wants one. If you cannot say how playing teaches the concept, make an interactive visual instead.

## Design before code

Write these four lines as a comment at the top of `App.tsx` before building anything:

1. **Concept to mechanic:** "The player does X; X is the concept because ..."
2. **Core loop (30 seconds or less):** see the state → decide → act → get feedback.
3. **Feedback that teaches:** why a move worked or failed, in the concept's terms, not just points.
4. **Progression:** three to seven rounds, each adding exactly one twist, with difficulty that ramps.

## Shape

1. **Predict:** ask "how will you do?" with the kit's `Predict`, which needs no `correct` answer.
2. **First round:** a one-sentence instruction, then play.
3. **Rounds:** the escalating rounds themselves.
4. **Debrief:**
   - compare the result with the prediction;
   - state the concept plainly;
   - ask one "what would you do differently".
5. **Replay:** one button.

The example game that `workbench new` creates follows this shape. Replace its mechanic, and keep the structure.

## Rules

- **Fast to start.** It is playable within 10 seconds, with at most two sentences of on-screen instructions.
- **Any input.** Keyboard, pointer, and touch all work. Targets are at least 44 px and the game works at 375 px wide.
- **Fair randomness.** Use seeded or deterministic randomness so rounds are fair and failures can be explained.
- **Kit state, kit loop.**
  - State goes in a `createStore`.
  - Motion runs through `useGameLoop`, never `setInterval`.
  - Discrete actions use `useKeyPress`.
- **Rendering.** Use DOM or SVG for a few dozen moving things, and `<canvas>` beyond that.
- **The debrief matters more than the score.** No sound unless the user asks.

## Build

1. `workbench new <topic>/kept/<name>/src`, or a scratch folder when nothing is kept yet.
2. Edit `App.tsx` while `workbench dev` runs.
3. `workbench build <src> <topic>/kept/<name>/<name>.html --title "..."`.
4. Check it before showing.

## Common misses

- A quiz with points bolted on: the mechanic has nothing to do with the concept.
- A long intro before any play.
- No debrief.
- A first round that is too hard.
- Failure with no explanation.
