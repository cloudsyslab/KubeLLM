import type { ComponentType, LazyExoticComponent } from "react";
import { OPTIONS as COMPARE } from "./compare";
import { OPTIONS as DOCK } from "./dock";
import { OPTIONS as ENVIRONMENT } from "./environment";
import { OPTIONS as EXECUTION } from "./execution";
import { OPTIONS as JOBS } from "./jobs";
import { OPTIONS as LAUNCH } from "./launch";
import { OPTIONS as PUBLISH } from "./publish";
import { OPTIONS as RESOURCES } from "./resources";
import { OPTIONS as RUNS } from "./runs";
import { OPTIONS as TOPOLOGY } from "./topology";

export type Surface = "runs" | "compare" | "execution" | "launch" | "environment" | "jobs" | "publish" | "resources" | "topology" | "dock";

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

export interface SurfaceDef {
  id: Surface;
  label: string;
  group: "Evaluate" | "Operate" | "Lab" | "App-wide";
  /** Page that shows the picked option; null for app-wide pieces. */
  path: string | null;
  question: string;
  title: string;
  description: string;
  options: OptionDef[];
}

// Each surface owns its option list in ./<surface>/index.ts.
export const SURFACES: SurfaceDef[] = [
  { id: "runs", label: "Runs", group: "Evaluate", path: "/runs", title: "Runs", question: "How should the run history be browsed?", description: "Every recorded run across canonical, exploratory, and local sources.", options: RUNS },
  { id: "compare", label: "Compare", group: "Evaluate", path: "/compare", title: "Compare", question: "How should two to eight runs be compared?", description: "Runs side by side on the cases they share.", options: COMPARE },
  { id: "execution", label: "Execution", group: "Operate", path: "/execution", title: "Execution", question: "What should a live campaign lead with?", description: "Live view of the running campaign: progress, the current attempt's phases, and redacted output.", options: EXECUTION },
  { id: "launch", label: "New campaign", group: "Operate", path: "/launch", title: "New campaign", question: "How should a campaign be planned and started?", description: "Plan a serial campaign through the canonical runner, gated by fresh readiness.", options: LAUNCH },
  { id: "environment", label: "Environment", group: "Operate", path: "/environment", title: "Environment", question: "How should lane readiness be shown and acted on?", description: "Readiness of the selected private lane, with explicit preflight and preparation.", options: ENVIRONMENT },
  { id: "jobs", label: "Jobs", group: "Operate", path: "/jobs", title: "Jobs", question: "How should operator jobs be listed?", description: "Preflight, preparation, campaign, and publication jobs with their outcomes.", options: JOBS },
  { id: "publish", label: "Publish", group: "Operate", path: "/publish", title: "Publish results", question: "How should a sanitized export be reviewed before it is committed?", description: "Review the sanitized exploratory pack for a completed campaign, then publish it.", options: PUBLISH },
  { id: "resources", label: "Lab resources", group: "Lab", path: "/lab", title: "Resources", question: "How dense should the host and GPU view be?", description: "Host, memory, disk, and GPU activity on the lab server, with the processes behind them.", options: RESOURCES },
  { id: "topology", label: "Topology", group: "Lab", path: "/lab/topology", title: "Topology", question: "How should the lab's clusters and services be explored?", description: "Cluster profiles, services, and dependencies on the lab, read-only. Actions stay confined to the selected private lane.", options: TOPOLOGY },
  { id: "dock", label: "Active work", group: "App-wide", path: null, title: "Active work", question: "How should running work stay visible on every page?", description: "The app-wide indicator for the running job.", options: DOCK },
];

export const surfaceDef = (surface: Surface) => SURFACES.find((s) => s.id === surface)!;
