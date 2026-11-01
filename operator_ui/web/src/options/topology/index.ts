import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Structured map",
    idea: "Profiles side by side; the selected lane expands into node, namespaces, and pods with explanations.",
    optimizes: "Reading pod health and knowing which problems are expected.",
    tradeoff: "Relationships are implied by nesting rather than drawn.",
    reference: "Kubernetes dashboards, Railway services",
    recommended: true,
    component: lazy(() => import("./StructuredMap")),
  },
  {
    id: "b",
    letter: "B",
    name: "Node graph",
    idea: "An interactive graph from host to profiles, node, namespaces, and pods, with a side panel.",
    optimizes: "Seeing how components connect.",
    tradeoff: "A small lab leaves the canvas sparse; pod detail needs clicks.",
    reference: "React Flow graphs",
    component: lazy(() => import("./NodeGraph")),
  },
];
