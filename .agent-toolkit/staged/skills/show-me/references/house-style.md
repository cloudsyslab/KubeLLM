# House style

The decision record for how `show-me` artifacts look. Read it before changing `assets/house-tokens.css`, `assets/house-base.css`, the layouts, or the workbench theme, so a change extends the system instead of drifting from it.

## Direction

Dark-first engineering editorial: the look of good developer documentation and engineering blogs. It was derived from measured reference pages, not invented: near-black canvases, a clean grotesk body, light or medium display weights with tight tracking, a mono voice for metadata, docs and article frames, hairlines instead of boxes, and one accent.

## Principles

1. **Dark by default.** The canvas is near-black (`--bg`), never pure black text on white. Dark wins whatever the viewer's OS prefers; light is a remembered choice through the toggle. Both themes are designed, not inverted.
2. **Text is never pure white.** Three levels: `--fg` for headings and emphasis, `--fg-2` for reading text, `--fg-3` for metadata. Reading text sits at the second level so headings carry the hierarchy.
3. **Three voices.**
   - Body: Geist at 16 px for UI, 17 px with 1.7 line height for prose.
   - Display: Geist, weight 500, tracked about −0.035em.
   - Mono labels: Geist Mono at 12 px, uppercase, tracked 0.08em, for one-to-four-word metadata only. A sentence in the mono voice shouts.
   - Blog titles alone use Newsreader at a light weight, the editorial exception that separates "a piece to read" from "a reference to navigate."
4. **One accent.** `--signal` (pink) marks the one primary action, focus, "you are here," the predict ritual, and hero art. Links are text-colored with a faint underline that turns signal on hover. Status colors appear only with a word.
5. **Hairlines, not boxes.** Structure comes from 1 px borders at about 9–16% of the text color and from spacing. No drop shadows on content; radius stays tight (6 px), 10 px only for hero art.
6. **Frames from documentation.** The map and blog use a sticky top bar with mono breadcrumbs, a 248 px left sidebar of 14 px links on 32 px rows, a centered column up to 760 px, and a right rail ("On this page" or artifacts) that disappears below 1200 px. Below 900 px the sidebar folds into a toggle.
7. **One rich moment per artifact.** A blog gets a seeded gradient hero; a map gets its territory tree. Everything else stays quiet so that moment lands.
8. **Diagrams like system diagrams.** Hairline boxes, mono labels, and a single tinted primary path.

## Measured references (October 2026)

- Docs: background about `#0d0a0f`, headings `#e5e0e4` at 62 px weight 500 tracked −0.04em, body 18/28 in a warm gray, sidebar 271 px with 14 px links on 32 px rows, content 816 px, one magenta accent, square corners.
- Engineering blog: pure black background, text `#dcdcdc`, title 30 px weight 600 centered over an 18 px subtitle, body 16/25.6 in an 872 px column, 194 px sidebar with an 8 px-radius soft active fill, gradient hero with 10 px radius, code blocks drawn with a 0.5 px hairline.
- Brand pages: `#0c0c0c` canvas, light serif display at weight 300 tracked −0.02em, Geist body at weight 300, Geist Mono uppercase labels at 11–12 px tracked about 0.08em.

## Changing the look

- Colors, type, and spacing change in `house-tokens.css` only; component shape and layout change in `house-base.css`. The workbench imports the tokens and maps them in `assets/workbench/src/styles.css`.
- Re-run the categorical palette through a data-visualization validator against both `--surface` values after any series change.
- Check text contrast: `--fg-3` must stay at 4.5:1 or better on `--bg` in both themes.
- Render the `page`, `map`, and `blog` layouts and the example game at desktop and phone widths in both themes before shipping a change.
