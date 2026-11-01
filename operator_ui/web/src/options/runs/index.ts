import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Experiments table",
    idea: "One dense, sortable row per run with search, source/technique/model/status filters, and checkboxes that fill a compare tray.",
    optimizes: "Finding any run among 115 by any column, then picking 2–8 to compare.",
    tradeoff: "Repetitions of a configuration are scattered rows; run-to-run spread is not visible at a glance.",
    reference: "Braintrust experiments list, Linear filter chips",
    recommended: true,
    component: lazy(() => import("./ExperimentsTable")),
  },
  {
    id: "b",
    letter: "B",
    name: "Timeline",
    idea: "Runs over time in one swimlane per debug model: length is duration, height is Ground Truth success. Brush the overview to zoom.",
    optimizes: "Seeing when campaigns ran, back-to-back repetitions, and drift between periods.",
    tradeoff: "The history is clustered in a few weeks, so most work happens zoomed in; exact values need a hover or the list below.",
    reference: "Vercel deployments timeline, Modal app history",
    component: lazy(() => import("./Timeline")),
  },
  {
    id: "c",
    letter: "C",
    name: "By configuration",
    idea: "Runs grouped under their configuration, each with a strip of per-run bars, spread, and expandable per-case squares per run.",
    optimizes: "Repetition-aware picking: run-to-run spread, cases that flip, and one-click compare of a configuration's repetitions.",
    tradeoff: "Less suited to scanning by date or sorting individual runs; per-run detail sits one expand away.",
    reference: "Explorer leaderboard, CI build matrices",
    component: lazy(() => import("./Configurations")),
  },
];
