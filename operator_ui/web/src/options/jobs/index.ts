import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "B+C+A",
    name: "Activity feed on a time axis",
    idea: "The running campaign on top, then jobs as a story grouped into working sessions. Each session shows the operator lock and every job's span on one axis, with the idle time between jobs stated. Search, kind, and status filters scope it all; entries expand in place to their step timeline.",
    optimizes: "Reading what happened in order, how long it took, where the lab sat idle, and how preflight, preparation, campaign, and publication connect, while still finding a job by name or status.",
    tradeoff: "Taller than a table; 30-second preflights are slivers beside 8-hour campaigns on a shared axis.",
    reference: "GitHub activity feed, GitHub Actions job timing, GitHub Actions runs filters",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./JobsFeed")),
  },
];
