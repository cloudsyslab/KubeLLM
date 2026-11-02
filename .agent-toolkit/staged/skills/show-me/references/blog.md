# Blog

Carry an argument from start to finish with live figures, at a quality someone else could read cold: a learning session's closing write-up, a frontier summary, or an explainer worth sending to a friend. Built as a single file from the `blog` layout (see [building.md](building.md)).

## Structure

1. **Masthead.**
   - Kicker: the topic.
   - Title: the thesis, as a sentence.
   - Dek: why it matters, plus an estimated reading time.
2. **Hook.** Open with a concrete example or question the reader already recognizes.
3. **Body.** Write three to six sections. Each section heading is a claim, and each section moves claim → evidence → figure or worked example → "so what".
4. **Predict moments.** Add one or two predict blocks right before the most surprising reveals.
5. **What is unsettled.** Cover open questions, real disagreements, and what evidence would change the conclusion.
6. **Position.** State the author's current take, bounded by what the evidence supports. In a learning session, this is the learner's position, in their words, tightened.
7. **Sources.** List them with links, primary sources first.

## Writing

- **Plain words.** Define each term the first time it appears and keep paragraphs short.
- **Cite as you go.** Link each claim where it appears, and mark the difference between a sourced fact and your inference.
- **Highlight sparingly.** Use at most one `mark` per section.
- **Mind the length.** Aim for 900 to 2,000 words. A longer piece should become two posts.

## Figures

- **Keep them small.** Inline each interactive visual in its own `.figure` with a caption.
- **Reuse kept visuals.** Copy their figure markup and code in rather than linking out.
- **Show the moment the argument turns on.** Put a figure there, not on every section.

## Fast path

Run `artifact.py new <out.html> --layout blog --title "<thesis>" --kicker "<topic>"`, write the sections inside `.prose` with claim headings (the rail builds itself from them), and add figures where the argument needs them. Keep the serif title, the seeded hero, and the sidebar links to the topic's map and kept artifacts.

## Common misses

- Section titles that only name topics.
- A wall of text with one figure at the end.
- Claims with no source.
- A conclusion that hedges everything.
- Leftover layout placeholders.
