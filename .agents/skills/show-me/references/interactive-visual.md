# Interactive visual

Make one mechanism visible and let the user act on it. Built as a single file (see [building.md](building.md)).

## When

Use it for motion, flow, sequence, parameters, tradeoffs, or a structure worth drilling into: anywhere a static picture would hide the point. If the idea needs two separate figures to land, it is a blog.

## Pick one shape

- **Step-through:** a sequence such as a request's path or an algorithm's passes. Each step changes the same figure, and the caption says what just changed.
- **Explorable:** one or two parameters drive the figure, and the consequence shows immediately. Mark the threshold where behavior changes.
- **Drill-down:** an overview first; clicking a part expands its detail beside it, not in a modal.
- **Compare:** two states side by side, or an A/B toggle, on the same axes and scale.

## Anatomy

1. **Masthead.** The title states the insight ("Past five judges, agreement barely moves"), not the topic ("LLM judges").
2. **Predict block.** It asks what the user expects and unlocks the figure on reveal.
3. **Figure.** Controls go above the visual. Its default state already shows something worth noticing. The caption names what to notice.
4. **Takeaway.** One callout states the takeaway in a sentence.
5. **Optional nudge.** One or two "try this" prompts point at the interesting region.

## Quality bar

- **One idea.** Cut every control that does not serve it.
- **Real labels and numbers** from the conversation or its sources. Label illustrative data as illustrative.
- **Immediate feedback.** No "Run" button for anything that computes in under 100 ms. Control ranges cover the interesting region, not the full theoretical range.
- **Phone first.** It works at 375 px: controls stack above the figure, the SVG uses `viewBox` and scales, and touch targets are at least 40 px.
- **Accessible.** The figure has an `aria-label`, controls work from the keyboard, and identity never depends on color alone.
- **Motion with a purpose.** Animate only to show change between states.

## Fast path

The `page` layout, then SVG, then 30 to 80 lines of render code driven by the controls. Reach for `d3` scales or shapes only when hand math gets fiddly.

## Common misses

- A static picture dressed up with a slider that changes nothing important.
- A figure that only makes sense after reading the caption.
- Unlabeled axes or units.
- Too many controls at once.
- A default state where nothing is happening.
