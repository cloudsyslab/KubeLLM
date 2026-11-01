import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "A+B",
    name: "Metric rows with the case matrix",
    idea: "One run is the base; rows of metrics show every run's value, its delta, and how many shared cases flipped. Below, the flipped cases per run, which expand into the full case diff matrix.",
    optimizes: "Answering \"what changed against this run\" in one read, then which cases, without leaving the page.",
    tradeoff: "The matrix stays folded until asked for; with eight runs it scrolls sideways on a phone.",
    reference: "Braintrust experiment comparison and per-row diff",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./Compare")),
  },
];
