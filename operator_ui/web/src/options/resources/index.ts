import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Dense instrument",
    idea: "btop-style: per-thread load, per-GPU tiles, sparklines, and a live process table.",
    optimizes: "Spotting which process and which GPU is busy right now.",
    tradeoff: "More to scan; history is short.",
    reference: "btop and htop",
    recommended: true,
    component: lazy(() => import("./DenseInstrument")),
  },
  {
    id: "b",
    letter: "B",
    name: "Calm charts",
    idea: "A few large time-series panels with current values, processes tucked below.",
    optimizes: "Trends over the last few minutes at a glance.",
    tradeoff: "Per-thread and per-process detail is reduced.",
    reference: "Vercel and Datadog observability",
    component: lazy(() => import("./CalmCharts")),
  },
];
