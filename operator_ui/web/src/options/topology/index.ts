import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "A+C+D",
    name: "Structured map with an explanation panel",
    idea: "The containment tree (host, then the lane) beside a wide panel that explains the selected component: why it's in its state, what it needs and what needs it by hop distance, and, on request, why each thing fails with it. A Timeline switch shows every component's health at every phase of the campaign, explained by the same panel.",
    optimizes: "Reading the whole lab's health with names and statuses in full, then asking one component what it does, what it's part of, and what breaks if it breaks.",
    tradeoff: "Relationships are listed, not drawn: the chain reads hop by hop in the panel rather than as lines on a canvas.",
    reference: "Kubernetes dashboards and Railway services for the tree, dbt lineage for the hop view, Datadog host maps over time",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./TopologyExplorer")),
  },
];
