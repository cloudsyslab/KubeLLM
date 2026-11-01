import { lazy, type ComponentType, type LazyExoticComponent } from "react";
import type { OptionDef } from "../registry";

/** Where an active-work option renders app-wide. */
export type DockSlot = "sidebar" | "topbar" | "floating";

export interface DockGlobal {
  slot: DockSlot;
  component: LazyExoticComponent<ComponentType>;
}

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

/** App-wide renderers keyed by option id. */
export const GLOBAL: Record<string, DockGlobal> = {};
