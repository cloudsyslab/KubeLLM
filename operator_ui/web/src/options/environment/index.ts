import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "B+A",
    name: "Health board with CI steps",
    idea: "Dependency cards in three zones under the freshness ring, then the run beneath them as CI steps in run order. Each step opens its terminal: the commands it ran with stdin, stdout, stderr, and exit codes, drawn like Execution's output. A card jumps to its dependency's most telling check; during a run the terminal follows the running check.",
    optimizes: "Seeing which dependency is unhealthy at a glance, then reading exactly what its check ran and printed, and what preparation can do about it.",
    tradeoff: "A long page: the board, the steps, and the terminal are stacked; on phones the terminal opens under its step.",
    reference: "Railway service canvas over GitHub Actions job steps and logs",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./LaneHealth")),
  },
];
