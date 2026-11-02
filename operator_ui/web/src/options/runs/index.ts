import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "A+B",
    name: "Experiments table with a timeline view",
    idea: "One dense, sortable row per run with search, source/technique/model/status filters, and checkboxes that fill a compare tray. A Timeline switch draws the same filtered runs over time, one swimlane per debug model, with a brushable overview.",
    optimizes: "Finding any run by any column, seeing when campaigns ran and how repetitions drifted, and picking 2–8 to compare from either view.",
    tradeoff: "Two views to learn; the timeline only places runs whose ID carries a start time, and exact values there need a hover or the list below it.",
    reference: "Braintrust experiments list, Linear filter chips and view switch, Vercel deployments timeline",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./RunsBrowser")),
  },
];
