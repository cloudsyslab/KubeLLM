import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Structured map",
    idea: "A containment tree in two columns, host then lane, with a persistent inspector. Selecting a row marks its dependencies and dependents everywhere.",
    optimizes: "Reading every component's health and why, with names and statuses in full.",
    tradeoff: "Relationships show as row marks, not drawn lines; the path between two components takes reading.",
    reference: "Kubernetes dashboards, Railway services, Linear lists",
    component: lazy(() => import("./StructuredMap")),
  },
  {
    id: "b",
    letter: "B",
    name: "Dependency graph",
    idea: "The lab as a drawn map: nested frames for host, Docker, and the lane; edges for calls and routing, lit by the current phase. Click a node, then ask what fails with it.",
    optimizes: "Clicking around: seeing what connects to what, where traffic flows now, and the blast radius in place.",
    tradeoff: "A canvas to pan and zoom; on phones it starts as a list.",
    reference: "Datadog service map, React Flow",
    recommended: true,
    component: lazy(() => import("./DependencyGraph")),
  },
  {
    id: "c",
    letter: "C",
    name: "Blast radius",
    idea: "One component at the center: what it needs fans out to the left by hop distance, what fails with it fans out to the right. Click anything to re-center.",
    optimizes: "Answering \"what breaks if this breaks\" and walking a failure chain one hop at a time.",
    tradeoff: "Shows one neighborhood at a time, never the whole lab.",
    reference: "dbt lineage, Honeycomb service map drill-down",
    component: lazy(() => import("./BlastRadius")),
  },
  {
    id: "d",
    letter: "D",
    name: "Health timeline",
    idea: "Components down the side, every phase of every attempt across the top. Each cell is that component's health and traffic at that moment; click one to inspect or replay it.",
    optimizes: "Answering what was affected, and when, across the whole campaign so far.",
    tradeoff: "Time, not structure: you see that two rows changed together, not how they connect.",
    reference: "Datadog host map over time, CI build matrices",
    component: lazy(() => import("./HealthTimeline")),
  },
];
