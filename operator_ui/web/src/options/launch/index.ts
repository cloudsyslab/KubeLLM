import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Builder and plan rail",
    idea: "Every input on one page, with a sticky rail that keeps the attempt count, estimates, and the readiness gate in view while you edit.",
    optimizes: "The common case: a model or two across a case set, adjusted and launched in under a minute.",
    tradeoff: "A long page; on phones the rail becomes a bottom bar and estimates move into the review.",
    reference: "Vercel new project, Linear create forms",
    recommended: true,
    component: lazy(() => import("./OnePageBuilder")),
  },
  {
    id: "b",
    letter: "B",
    name: "Guided steps",
    idea: "One decision per step; finished steps collapse to a summary and a running tally fills in, ending in a review step before the final confirmation.",
    optimizes: "Occasional operators and anyone who wants each choice explained in order.",
    tradeoff: "Slower for repeat launches; changing an early step means jumping back.",
    reference: "Stripe and Vercel onboarding steppers",
    component: lazy(() => import("./GuidedSteps")),
  },
  {
    id: "c",
    letter: "C",
    name: "Composer",
    idea: "A keyboard-first sentence (run cases with models using technique × repetitions) with a filterable list, an inspector, and the exact request, manifest, and run order.",
    optimizes: "Fast keyboard use and checking exactly what is sent and in what order.",
    tradeoff: "Less browsable; history is one item at a time in the inspector.",
    reference: "Raycast and Linear command menus",
    component: lazy(() => import("./Composer")),
  },
  {
    id: "d",
    letter: "D",
    name: "Matrix planner",
    idea: "Cases as rows and models as columns; each cell shows recorded Ground Truth history, and history-based selections pick coverage gaps or unstable cases.",
    optimizes: "Deciding which cases to rerun from what the evidence already shows.",
    tradeoff: "Wide; cells look selectable but a campaign is always a full product of rows and columns.",
    reference: "Braintrust experiment grids, the explorer's case matrix",
    component: lazy(() => import("./MatrixPlanner")),
  },
];
