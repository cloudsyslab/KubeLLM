import { lazy } from "react";
import type { OptionDef } from "../registry";

// Placeholder until this surface's options are built.
export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "In progress",
    idea: "Options for this surface are being built.",
    optimizes: "—",
    tradeoff: "—",
    reference: "—",
    component: lazy(() => import("../Placeholder")),
  },
];
