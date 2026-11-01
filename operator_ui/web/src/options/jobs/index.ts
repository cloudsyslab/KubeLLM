import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Ledger",
    idea: "Every job in one dense, filterable table. A drawer opens the job's timeline, readiness checks, linked runs, or published pack; j and k step through jobs.",
    optimizes: "Finding a job fast and reading why it ended, at the operator's 30-job history.",
    tradeoff: "Sequence and idle gaps between jobs stay implicit; the drawer covers the list on phones.",
    reference: "GitHub Actions runs, Vercel deployments, Linear peek",
    recommended: true,
    component: lazy(() => import("./Ledger")),
  },
  {
    id: "b",
    letter: "B",
    name: "Activity feed",
    idea: "The running campaign on top, then jobs grouped by day as a story. Entries expand in place and link to the job that unblocked, gated, or published them.",
    optimizes: "Reading what happened in order, and how preflight, preparation, campaign, and publication connect.",
    tradeoff: "Slower to scan or filter by status; a long history gets tall.",
    reference: "GitHub activity feed, Vercel activity log",
    component: lazy(() => import("./Feed")),
  },
  {
    id: "c",
    letter: "C",
    name: "Timeline",
    idea: "Jobs on a time axis: a strip of working sessions with idle days collapsed, then the chosen session as a waterfall with the operator lock's busy and idle time.",
    optimizes: "Seeing duration, order, the one-job-at-a-time lock, and where the lab sat idle.",
    tradeoff: "Weak for lookup by name or status; 30-second preflights are slivers beside 8-hour campaigns.",
    reference: "GitHub Actions job timing, DevTools waterfall, Gantt",
    component: lazy(() => import("./Timeline")),
  },
];
