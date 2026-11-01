import { lazy, type ComponentType, type LazyExoticComponent } from "react";
import type { OptionDef } from "../registry";

/** Where the active-work indicator renders app-wide. */
export type DockSlot = "topbar";

export interface DockGlobal {
  slot: DockSlot;
  component: LazyExoticComponent<ComponentType>;
}

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "B",
    name: "Top bar pill",
    idea: "A status pill in the top bar, docked into the mobile header below 1024px. Its popover holds the current attempt, recent outcomes, Stop, and Open execution.",
    optimizes: "Always visible on every page at every width, without covering content.",
    tradeoff: "Detail takes a click; on Execution it shrinks to a quiet count.",
    reference: "Vercel's deployment status, macOS menu bar extras",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./TopbarPill")),
  },
];

/** App-wide renderers keyed by option id. */
export const GLOBAL: Record<string, DockGlobal> = {
  chosen: { slot: "topbar", component: lazy(() => import("./TopbarPill").then((m) => ({ default: m.TopbarPillGlobal }))) },
};
