import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "A",
    name: "Dense instrument",
    idea: "btop-style: per-thread load, per-GPU tiles, sparklines, and a live process table.",
    optimizes: "Spotting which process and which GPU is busy right now.",
    tradeoff: "More to scan; history is short.",
    reference: "btop and htop",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./DenseInstrument")),
  },
];
