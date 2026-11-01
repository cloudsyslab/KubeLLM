import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "CI checklist",
    idea: "Checks as collapsible steps in run order with their durations, streaming in like a CI job; problems open by themselves and the history sits beside them.",
    optimizes: "Answering “is the lane ready, and if not, which check and why” in one read.",
    tradeoff: "A list, not a map: how dependencies relate is left to the group names.",
    reference: "GitHub Actions job steps, Vercel build logs",
    recommended: true,
    component: lazy(() => import("./ChecklistCI")),
  },
  {
    id: "b",
    letter: "B",
    name: "Health board",
    idea: "The same checks regrouped into dependency cards (cluster, RAG API, pgvector, providers, storage) with a freshness ring and a detail panel saying what preparation may repair.",
    optimizes: "Seeing which service is down at a glance and whether preparation can fix it.",
    tradeoff: "Cards cost height; run order and per-check timing are one click deeper.",
    reference: "Status pages, Railway service canvas",
    component: lazy(() => import("./HealthBoard")),
  },
  {
    id: "c",
    letter: "C",
    name: "Timeline and diff",
    idea: "Every preflight and preparation on one timeline; pick two runs to see only the checks that changed, with the repairs that happened in between.",
    optimizes: "Explaining why the lane went from blocked to ready, or the reverse.",
    tradeoff: "The current state is a summary line; reading a single run in full is less direct.",
    reference: "Vercel deployment history, GitHub compare",
    component: lazy(() => import("./RunTimeline")),
  },
];
