import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Metric rows",
    idea: "One run is the base; rows of metrics show every run's value, its delta, and how many shared cases improved or regressed, then the cases that flipped.",
    optimizes: "Answering \"what changed against this run\" in one read, with the flipped cases one hover away.",
    tradeoff: "Per-case detail is limited to flips; unchanged cases and per-case timings stay hidden.",
    reference: "Braintrust experiment comparison",
    recommended: true,
    component: lazy(() => import("./MetricRows")),
  },
  {
    id: "b",
    letter: "B",
    name: "Case diff matrix",
    idea: "Cases by runs, grouped by scenario: each cell is the attempt's Ground Truth outcome (or time, or tokens), with flips against the base marked.",
    optimizes: "Auditing exactly which cases differ, with a filter for differences, regressions, or improvements.",
    tradeoff: "Headline metrics are reduced to pass counts; wide with eight runs on a phone.",
    reference: "Braintrust per-row diff, explorer case matrix",
    component: lazy(() => import("./CaseDiff")),
  },
  {
    id: "c",
    letter: "C",
    name: "Visual",
    idea: "Numbered markers per run on each metric line, a time-against-success scatter with uncertainty whiskers, and per-scenario bars, all hover-linked.",
    optimizes: "Seeing the shape of a comparison: tradeoffs, spread, and whether gaps exceed sampling noise.",
    tradeoff: "Exact deltas and flipped cases need hovering; charts take more height than a table.",
    reference: "Artificial Analysis charts, W&B Weave comparisons",
    component: lazy(() => import("./Visual")),
  },
];
