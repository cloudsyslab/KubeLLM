import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Console first",
    idea: "The output stream is the page: an activity histogram over a dense, filterable log.",
    optimizes: "Reading exactly what ran and what it printed.",
    tradeoff: "Campaign progress and per-attempt outcomes are secondary.",
    reference: "Modal app logs",
    component: lazy(() => import("./ConsoleFirst")),
  },
  {
    id: "b",
    letter: "B",
    name: "Trace first",
    idea: "Attempts as a trace tree with a phase waterfall, and a detail drawer for the selected span.",
    optimizes: "Understanding one attempt's timing and each phase's output.",
    tradeoff: "The whole campaign is a list; less at-a-glance progress.",
    reference: "Braintrust traces",
    component: lazy(() => import("./TraceFirst")),
  },
  {
    id: "c",
    letter: "C",
    name: "Attempt grid first",
    idea: "Every planned attempt as a grid that fills in live, then the current attempt's phases, then a log tail.",
    optimizes: "Campaign progress with a real denominator, in the explorer's visual language.",
    tradeoff: "Full output is one step away (expand the log).",
    reference: "Explorer case matrix, CI matrices",
    recommended: true,
    component: lazy(() => import("./GridFirst")),
  },
];
