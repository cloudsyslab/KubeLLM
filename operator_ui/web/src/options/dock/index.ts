import { lazy, type ComponentType, type LazyExoticComponent } from "react";
import type { OptionDef } from "../registry";

/** Where an active-work option renders app-wide. */
export type DockSlot = "sidebar" | "topbar" | "floating";

export interface DockGlobal {
  slot: DockSlot;
  component: LazyExoticComponent<ComponentType>;
}

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Sidebar card",
    idea: "A compact card above the sidebar footer: attempts done of planned, the current attempt and phase, and a link to Execution. One quiet line when idle.",
    optimizes: "Glanceable detail on desktop without a click.",
    tradeoff: "On phones it sits inside the navigation sheet, one tap away; it adds height to the sidebar.",
    reference: "Slack's huddle card, Spotify's now-playing in the sidebar",
    component: lazy(() => import("./SidebarCard")),
  },
  {
    id: "b",
    letter: "B",
    name: "Top bar pill",
    idea: "A status pill in the top bar (docked into the mobile header below 1024px). Its popover holds the current attempt, recent outcomes, Stop, and Open execution.",
    optimizes: "Always visible on every page at every width, without covering content.",
    tradeoff: "Detail takes a click; the phone dock is a fixed overlay until the shell gets a header slot.",
    reference: "Vercel's deployment status, macOS menu bar extras",
    recommended: true,
    component: lazy(() => import("./TopbarPill")),
  },
  {
    id: "c",
    letter: "C",
    name: "Floating mini panel",
    idea: "A bottom-right panel with the attempt grid, current phase, and the latest output line. It collapses to a remembered pill and is always a pill on phones.",
    optimizes: "Watching a campaign while working on another page.",
    tradeoff: "Covers a corner of every page; the most visual noise of the three.",
    reference: "Google Drive's upload panel, Loom's recorder",
    component: lazy(() => import("./FloatingPanel")),
  },
];

/** App-wide renderers keyed by option id. */
export const GLOBAL: Record<string, DockGlobal> = {
  a: { slot: "sidebar", component: lazy(() => import("./SidebarCard").then((m) => ({ default: m.SidebarCardGlobal }))) },
  b: { slot: "topbar", component: lazy(() => import("./TopbarPill").then((m) => ({ default: m.TopbarPillGlobal }))) },
  c: { slot: "floating", component: lazy(() => import("./FloatingPanel").then((m) => ({ default: m.FloatingPanelGlobal }))) },
};
