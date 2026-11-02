# Building artifacts

Read this before building any rich artifact. It covers the stack, the shipped layouts and workbench, the pinned libraries, and the check before showing. Paths are relative to the `show-me` skill directory. For why the house looks the way it does, read [house-style.md](house-style.md).

## Pick the stack

- **Single file** (interactive visuals, blogs, maps, small experiences): one self-contained HTML file with vanilla JS and SVG or Canvas, plus pinned libraries only when they earn their place. It opens from disk with no server or build step.
- **Workbench** (games, multi-step experiences, anything with several screens, real state, or polished controls): React 19, Tailwind 4, and shadcn-style components, built into one inlined HTML file that also opens from disk.
- **Never an app framework** such as Next.js for an artifact. Something that needs a server, a back end, or extra installs is a demo for the calling workflow, not an artifact.

## Single file

1. Run `python3 scripts/artifact.py new <out.html> --title "<insight as a sentence>" --layout <layout> --kicker "<topic>"`.

   | Layout | Use for | Frame |
   | --- | --- | --- |
   | `page` (default) | an interactive visual or any one-idea artifact | single centered column, theme toggle |
   | `map` | a learning session's topic map | top bar, branch sidebar, territory tree drawn from the sidebar, artifacts rail |
   | `blog` | a session's closing article, or any long read | top bar, topic sidebar, serif title, gradient hero, "On this page" rail, "Copy page" |
2. Replace the placeholder content and keep the structure. The house helpers (theme, predict, steps, table of contents, scroll tracking, copy page, hero art, territory, phone navigation) are already inlined.
3. Write artifact styles in the unlayered block of the `<style>` element; the house styles sit in a lower layer, so yours win.
4. Use CSS variables for every color so both themes work. Never hard-code a hex value in an artifact.

### House components

| Class or hook | Use |
| --- | --- |
| `.page` | single centered column with responsive gutters |
| `.masthead`, `.kicker`, `.dek` | title block: topic label, claim, and one-line why |
| `.label` | the mono voice: short metadata of one to four words, never a sentence |
| `.prose` | reading text for paragraphs, lists, and section heads |
| `.figure`, `figcaption` | hairline frame for every visual, with a one-line "what to notice" |
| `.diagram`, `.node`, `.node.is-primary` | box diagrams; tint only the path that matters |
| `.callout` (first child `.label`), `.callout.warn`, `.callout.quiet` | the takeaway, the caveat, or an aside |
| `.status.here` / `.researched` / `.unsettled` / `.open` | a dot plus a word for state; never color alone |
| `.section`, `.section-head`, `.sources` | a map branch or article section, and its numbered sources |
| `mark` | the one phrase that matters |
| `.controls`, `.control`, `output` | labeled sliders and inputs with their live value |
| `.btn`, `.btn.signal`, `.btn.ghost`, `.btn.sm`, `.chip` | actions (monochrome by default, signal for the one primary action) and toggleable choices |
| `.grid-2` | two columns on wide screens, stacked on phones |
| `.chart`, `.chart .label`, `.chart .grid line`, `.chart .axis line` | recessive axis text, direct labels, gridlines in SVG |
| `.num`, `.muted`, `.faint` | tabular figures and the two secondary text levels |
| `data-toc="<selector>"` | builds "On this page" from the h2s inside the selector |
| `data-spy` on a nav | marks the link for the section in view |
| `data-copy-page="<selector>"` | copies that region as light Markdown |
| `data-hero="<seed>"` | paints a gradient field seeded by the text, so each artifact gets its own |
| `data-territory="<nav selector>"` | draws the map's branch tree from a nav; links with `class="sub"` become children |

### Predict, then reveal

The learner commits before the figure answers. The figure named in `data-unlocks` stays locked until the reveal.

```html
<div class="predict" data-predict data-unlocks="#explore">
  <p>What happens to agreement when you add a third judge?</p>
  <div class="predict-choices">
    <button class="chip" type="button" data-choice="up" data-correct>It rises</button>
    <button class="chip" type="button" data-choice="flat">It stays flat</button>
  </div>
  <!-- or a free-text guess: <textarea data-guess></textarea> -->
  <div class="predict-actions">
    <button class="btn signal" type="button" data-reveal>Lock in and reveal</button>
    <button class="skip" type="button" data-skip>Skip</button>
  </div>
  <div data-answer><p>It rises, but each judge adds less than the last.</p></div>
</div>
```

Listen for `predict:reveal` (detail: `choice`, `guess`, `skipped`) to react, for example to start an animation from the learner's guess.

### Step-through

```html
<section data-steps tabindex="0">
  <div data-step>First, the request arrives…</div>
  <div data-step>Then the cache is checked…</div>
  <nav class="steps-nav">
    <button class="btn ghost sm" type="button" data-step-prev>Back</button>
    <span data-step-count></span>
    <button class="btn sm" type="button" data-step-next>Next</button>
  </nav>
</section>
```

Listen for `steps:change` (detail: `index`, `step`) and redraw the shared figure for that step. Arrow keys work when the section has focus. Redraw on `theme:change` if a figure bakes colors into canvas pixels.

### Libraries

Uncomment the `page` layout's import map (or add one) and keep only the entries the artifact imports. Prefer plain SVG and a few lines of JS for simple figures.

| Need | Import name | Pinned URL |
| --- | --- | --- |
| scales, shapes, transitions, force layouts | `d3` | `https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm` |
| quick statistical charts | `@observablehq/plot` | `https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/+esm` |
| diagrams from text | `mermaid` | `https://cdn.jsdelivr.net/npm/mermaid@12.2.0/dist/mermaid.esm.min.mjs` |
| hand-drawn sketch look | `roughjs` | `https://cdn.jsdelivr.net/npm/roughjs@4.6.6/bundled/rough.esm.js` |
| springs and timelines | `motion` | `https://cdn.jsdelivr.net/npm/motion@14.6.0/+esm` |
| 3D | `three` | `https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js` |

React no longer ships a script-tag build, so do not hand-roll React in a single file; use the workbench instead. Fonts (Geist, Geist Mono, and Newsreader for blog titles) come from Google Fonts in the layout head; offline, system faces take over and nothing breaks.

### Charts

- Color series with `--series-1` through `--series-6` in that fixed order; never cycle or skip.
- Keep text in `--fg` levels, never in a series color. Light-theme slots 3 to 5 sit below 3:1 contrast, so label those marks directly.
- Use one y-axis, thin marks, recessive grids (`--grid`), a legend for two or more series, and a hover tooltip on every mark.
- When the runtime provides a data-visualization skill, follow it for anything beyond a simple chart.

## Workbench

```text
python3 scripts/artifact.py workbench status              # needs: install | sync | none
python3 scripts/artifact.py workbench install             # only after the user approves
python3 scripts/artifact.py workbench new <src>           # start from the example game
python3 scripts/artifact.py workbench dev <src> --port 5174
python3 scripts/artifact.py workbench build <src> <out.html> --title "..."
```

- **Install once, with approval.** Tell the user it downloads about 100 MB of npm packages into `~/.show-me/workbench` (or `$SHOW_ME_WORKBENCH`), then run `install`. `sync` happens automatically when the toolkit's template or house style changed; a changed package list needs a fresh install, so ask again.
- **Source lives with the artifact.** `<src>/App.tsx` default-exports the artifact; sibling files are fine. The helper copies the source into the workbench to build it, so the workbench never holds anything worth keeping.
- **Imports available:**
  - `@/ui/<name>`: `button` (variants `default`, `signal`, `outline`, `ghost`, `secondary`, `destructive`, `link`), `card`, `badge`, `progress`, `slider`, `tabs`, `tooltip`, `dialog`.
  - `@/kit`: `useGameLoop`, `useKeys`, `useKeyPress`, `usePointer`, `createStore`, `useStore`, `saved`, `Predict`, `useSteps`, `StepNav`, `useTheme`, `ThemeToggle`.
  - `@/lib/utils`: `cn`.
  - Packages: `react`, `motion`, `lucide-react`, `radix-ui`.

  Nothing else is installed. A new package is a toolkit template change, which needs a reinstall and the user's approval.
- **House colors and type in Tailwind:** `bg-canvas`, `bg-surface`, `bg-surface-2`, `border-line`, `border-line-strong`, `text-fg`, `text-fg-2`, `text-fg-3`, `bg-signal`, `text-signal`, `bg-signal-soft`, `text-signal-ink`, `bg-mark`, `text-good`, `text-warn`, `text-bad`, `bg-series-1` through `bg-series-6`; `font-display`, `font-mono`, `font-serif`. shadcn names such as `bg-primary` (the signal) and `text-muted-foreground` map onto the same tokens.
- **Iterate** with `dev` running in the background and the preview open at `http://localhost:<port>` in the sidebar browser; edits under `<src>` sync live.
- **Ship** with `build`. Its JSON must report `not_inlined: []`. Never edit the installed workbench; template changes belong in this skill's `assets/workbench/` and reach every install on next use.

## Check before showing

- Open the file, or the dev server for a workbench artifact, following `$browser-workflow`. If the browser shows a static snapshot or blocks scripts for a local file, serve its folder instead: run `python3 -m http.server <port> --bind 127.0.0.1` from that folder in the background and open `http://127.0.0.1:<port>/<file>`.
- Stop every server you started (that one, or `workbench dev`) once the check is done.
- Capture desktop (about 1280 px wide) and phone (375 px) screenshots in the default dark theme, then switch to light and look again.
- Read the console: no errors, and no failed library loads.
- Tab through the controls. Confirm a predict block keeps the figure locked until the reveal.
- Confirm the default state already shows something worth noticing, and that nothing overlaps, clips, or scrolls sideways.

## Publishing

Publish only when the user asks. Where the runtime offers hosted artifacts (for example Claude's artifact publishing), publish the single HTML file. Its scripts use allowed, pinned CDNs, its only stylesheet is Google Fonts, and workbench output inlines everything else. Otherwise share the file path.
