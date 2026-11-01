import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "B+A",
    name: "Guided steps with a plan rail",
    idea: "One decision per step (models, cases, technique, repetitions, then confirm), with a sticky rail that totals the plan as you go and owns the review and start action; starters fill the steps for a repeat launch.",
    optimizes: "Exploring models and cases one choice at a time without losing sight of the attempt count, estimate, and readiness gate.",
    tradeoff: "More clicks than a single form for a known plan, softened by starters and by jumping to confirm from the rail; on phones the rail becomes a bottom bar and the estimate moves into the confirm step.",
    reference: "Stripe and Vercel onboarding steppers, checkout summaries",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./GuidedBuilder")),
  },
];
