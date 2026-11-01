import { lazy, type ComponentType, type LazyExoticComponent } from "react";

export type Surface = "execution" | "resources" | "topology";

export interface OptionDef {
  id: string;
  letter: string;
  name: string;
  idea: string;
  optimizes: string;
  tradeoff: string;
  reference: string;
  recommended?: boolean;
  component: LazyExoticComponent<ComponentType>;
}

export const SURFACES: { id: Surface; label: string; path: string; question: string; options: OptionDef[] }[] = [
  {
    id: "execution",
    label: "Execution",
    path: "/execution",
    question: "What should a live campaign lead with?",
    options: [
      {
        id: "a",
        letter: "A",
        name: "Console first",
        idea: "The output stream is the page: an activity histogram over a dense, filterable log.",
        optimizes: "Reading exactly what ran and what it printed.",
        tradeoff: "Campaign progress and per-attempt outcomes are secondary.",
        reference: "Modal app logs",
        component: lazy(() => import("./execution/ConsoleFirst")),
      },
      {
        id: "b",
        letter: "B",
        name: "Trace first",
        idea: "Attempts as a trace tree with a phase waterfall, and a detail drawer for the selected span.",
        optimizes: "Understanding one attempt's timing and each phase's output.",
        tradeoff: "The whole campaign is a list; less at-a-glance progress.",
        reference: "Braintrust traces",
        component: lazy(() => import("./execution/TraceFirst")),
      },
      {
        id: "c",
        letter: "C",
        name: "Attempt grid first",
        idea: "Every planned attempt as a grid that fills in live, then the current attempt's phases, then a log tail.",
        optimizes: "Campaign progress with a real denominator, in the explorer's visual language.",
        tradeoff: "Full output is one step away (expand the log).",
        reference: "Explorer case matrix, CI matrices",
        recommended: true,
        component: lazy(() => import("./execution/GridFirst")),
      },
    ],
  },
  {
    id: "resources",
    label: "Lab resources",
    path: "/lab",
    question: "How dense should the host and GPU view be?",
    options: [
      {
        id: "a",
        letter: "A",
        name: "Dense instrument",
        idea: "btop-style: per-thread load, per-GPU tiles, sparklines, and a live process table.",
        optimizes: "Spotting which process and which GPU is busy right now.",
        tradeoff: "More to scan; history is short.",
        reference: "btop and htop",
        recommended: true,
        component: lazy(() => import("./resources/DenseInstrument")),
      },
      {
        id: "b",
        letter: "B",
        name: "Calm charts",
        idea: "A few large time-series panels with current values, processes tucked below.",
        optimizes: "Trends over the last few minutes at a glance.",
        tradeoff: "Per-thread and per-process detail is reduced.",
        reference: "Vercel and Datadog observability",
        component: lazy(() => import("./resources/CalmCharts")),
      },
    ],
  },
  {
    id: "topology",
    label: "Topology",
    path: "/lab/topology",
    question: "How should the clusters on the lab be drawn?",
    options: [
      {
        id: "a",
        letter: "A",
        name: "Structured map",
        idea: "Profiles side by side; the selected lane expands into node, namespaces, and pods with explanations.",
        optimizes: "Reading pod health and knowing which problems are expected.",
        tradeoff: "Relationships are implied by nesting rather than drawn.",
        reference: "Kubernetes dashboards, Railway services",
        recommended: true,
        component: lazy(() => import("./topology/StructuredMap")),
      },
      {
        id: "b",
        letter: "B",
        name: "Node graph",
        idea: "An interactive graph from host to profiles, node, namespaces, and pods, with a side panel.",
        optimizes: "Seeing how components connect.",
        tradeoff: "A small lab leaves the canvas sparse; pod detail needs clicks.",
        reference: "React Flow graphs",
        component: lazy(() => import("./topology/NodeGraph")),
      },
    ],
  },
];

export const surfaceDef = (surface: Surface) => SURFACES.find((s) => s.id === surface)!;
