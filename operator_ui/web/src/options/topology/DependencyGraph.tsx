import "@xyflow/react/dist/style.css";
import {
  Background,
  EdgeLabelRenderer,
  getSmoothStepPath,
  Handle,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useNodesInitialized,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import clsx from "clsx";
import { Expand, Focus, List, Minus, Network, Plus, Scan, Shrink } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Segmented, Tag } from "@/components/ui";
import {
  downstream,
  EDGE_KIND,
  HEALTH,
  neighborhood,
  upstream,
  whatIf,
  type Effect,
  type Health,
  type Rollup,
  type TopoEdge,
  type TopoNode,
  type TopologyGraph,
  type WhatIf,
} from "@/demo/topologyGraph";
import { StageFallback } from "../OptionsRoom";
import {
  DemoTag,
  EffectChip,
  FilterBar,
  HEALTH_SHORT,
  HEALTH_TEXT,
  HealthMark,
  Inspector,
  LaneHealth,
  LiveDot,
  matchesFilter,
  NodeIcon,
  TrafficLine,
  useGraph,
  type FilterId,
} from "./shared";

// ---------------------------------------------------------------------------
// Layout: tiers from the outside in (external API, host processes, Docker, the
// lane's cluster), with containment drawn as nested frames instead of edges.

const W = 168;
const H = 52;
const SW = 124;
const SH = 40;
const COL = W + 28;
const PAD = 12;
const HEAD = 28;

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}
interface Placed extends Rect {
  id: string;
  small?: boolean;
  /** A collapsed namespace standing in for its pods. */
  group?: boolean;
}
interface FramePlaced extends Rect {
  id: string;
  depth: number;
  collapsible?: boolean;
}
interface Layout {
  cards: Placed[];
  frames: FramePlaced[];
  /** Member id → the collapsed namespace card that stands in for it. */
  proxy: Map<string, string>;
  channelY: number;
  rects: Map<string, Rect>;
}

const SYSTEM_ORDER = ["sys:kube-apiserver", "sys:etcd", "sys:kube-controller-manager", "sys:kube-scheduler", "sys:coredns", "sys:kube-proxy", "sys:storage-provisioner"];
const OTHER_PROFILES = ["profile:minikube", "profile:minh", "profile:lamap", "profile:xyz"];

function layoutGraph(graph: TopologyGraph, collapsed: Set<string>): Layout {
  const cards: Placed[] = [];
  const frames: FramePlaced[] = [];
  const proxy = new Map<string, string>();
  const place = (id: string, x: number, y: number, extra: Partial<Placed> = {}) => {
    if (graph.byId.has(id)) cards.push({ id, x, y, w: extra.small ? SW : W, h: extra.small ? SH : H, ...extra });
  };
  const col = (i: number) => PAD + i * COL;

  const hostY = 92;
  const rowA = hostY + HEAD;
  const rowB = rowA + H + 32;
  place("openai", col(1), 0);
  place("operator", col(0), rowA);
  place("worker", col(1), rowA);
  place("ollama", col(2), rowA);
  place("gpu-0", col(3), rowA);
  place("rag", col(0), rowB);
  place("gpu-1", col(3), rowB);
  const channelY = rowB + H + 16;

  const dockerX = PAD;
  const dockerY = rowB + H + 32;
  const dIn = { x: dockerX + PAD, y: dockerY + HEAD };
  place("pgvector", dIn.x, dIn.y);

  const profX = dIn.x;
  const profY = dIn.y + H + 20;
  const pIn = { x: profX + PAD, y: profY + HEAD };

  // default namespace
  let nsRight: number;
  let nsBottom: number;
  if (collapsed.has("ns:default")) {
    place("ns:default", pIn.x, pIn.y, { group: true });
    for (const id of ["fixture:pod", "fixture:svc", "fixture:ep", "pod:curl-pod", "pod:tmpcurl"]) proxy.set(id, "ns:default");
    nsRight = pIn.x + W;
    nsBottom = pIn.y + H;
  } else {
    const inner = { x: pIn.x + PAD, y: pIn.y + 26 };
    const gap = 16;
    place("pod:curl-pod", inner.x, inner.y);
    place("fixture:pod", inner.x + W + gap, inner.y);
    place("pod:tmpcurl", inner.x + 2 * (W + gap), inner.y);
    const row2 = inner.y + H + 24;
    place("fixture:svc", inner.x, row2);
    place("fixture:ep", inner.x + W + gap, row2);
    const w = PAD * 2 + 3 * W + 2 * gap;
    const h = 26 + H + 24 + H + PAD;
    frames.push({ id: "ns:default", x: pIn.x, y: pIn.y, w, h, depth: 3, collapsible: true });
    nsRight = pIn.x + w;
    nsBottom = pIn.y + h;
  }

  // kube-system and the node, in a column to the right
  const rx = nsRight + 16;
  let ksBottom: number;
  let ksRight: number;
  if (collapsed.has("ns:kube-system")) {
    place("ns:kube-system", rx, pIn.y, { group: true });
    for (const id of SYSTEM_ORDER) proxy.set(id, "ns:kube-system");
    ksBottom = pIn.y + H;
    ksRight = rx + W;
  } else {
    const inner = { x: rx + PAD, y: pIn.y + 26 };
    SYSTEM_ORDER.forEach((id, i) => place(id, inner.x + (i % 2) * (W + 16), inner.y + Math.floor(i / 2) * (H + 12)));
    const w = PAD * 2 + 2 * W + 16;
    const h = 26 + 4 * H + 3 * 12 + PAD;
    frames.push({ id: "ns:kube-system", x: rx, y: pIn.y, w, h, depth: 3, collapsible: true });
    ksBottom = pIn.y + h;
    ksRight = rx + w;
  }
  place("node:minh-lane", rx, ksBottom + 14);
  const profRight = Math.max(ksRight, rx + W) + PAD;
  const profBottom = Math.max(nsBottom, ksBottom + 14 + H) + PAD;
  frames.push({ id: "profile:minh-lane", x: profX, y: profY, w: profRight - profX, h: profBottom - profY, depth: 2 });

  const othersY = profBottom + 16;
  OTHER_PROFILES.forEach((id, i) => place(id, dIn.x + i * (SW + 10), othersY, { small: true }));
  const dockerRight = Math.max(profRight, dIn.x + 4 * SW + 30) + PAD;
  const dockerBottom = othersY + SH + PAD;
  frames.push({ id: "docker", x: dockerX, y: dockerY, w: dockerRight - dockerX, h: dockerBottom - dockerY, depth: 1 });

  const hostRight = Math.max(dockerRight, col(3) + W) + PAD;
  frames.push({ id: "host", x: 0, y: hostY, w: hostRight, h: dockerBottom + PAD - hostY, depth: 0 });

  const rects = new Map<string, Rect>();
  for (const r of [...frames, ...cards]) rects.set(r.id, r);
  return { cards, frames, proxy, channelY, rects };
}

// Hand-routed handles for the edges that would otherwise cross cards.
const ROUTES: Record<string, { s: string; t: string; lane?: number }> = {
  "operator>worker": { s: "r", t: "l" },
  "worker>openai": { s: "t", t: "b" },
  "worker>ollama": { s: "r", t: "l" },
  "ollama>gpu-0": { s: "r", t: "l" },
  "worker>rag": { s: "bl", t: "r" },
  "rag>pgvector": { s: "b", t: "t" },
  "worker>fixture:pod": { s: "b", t: "t", lane: 0 },
  "worker>ns:default": { s: "b", t: "t", lane: 0 },
  "worker>sys:kube-apiserver": { s: "br", t: "t", lane: 8 },
  "worker>ns:kube-system": { s: "br", t: "t", lane: 8 },
  "fixture:svc>fixture:ep": { s: "r", t: "l" },
  "fixture:ep>fixture:pod": { s: "t", t: "b" },
  "sys:kube-apiserver>sys:etcd": { s: "r", t: "l" },
  "sys:kube-controller-manager>sys:kube-apiserver": { s: "t", t: "b" },
  "sys:kube-scheduler>sys:kube-apiserver": { s: "t", t: "b" },
};

function autoRoute(a: Rect, b: Rect) {
  const dx = b.x + b.w / 2 - (a.x + a.w / 2);
  const dy = b.y + b.h / 2 - (a.y + a.h / 2);
  if (Math.abs(dy) > Math.abs(dx) * 0.6) return dy > 0 ? { s: "b", t: "t" } : { s: "t", t: "b" };
  return dx > 0 ? { s: "r", t: "l" } : { s: "l", t: "r" };
}

/** Drawn edges run from the caller to what it needs, so serves edges flip. */
const drawn = (edge: TopoEdge) => (edge.kind === "serves" ? { from: edge.target, to: edge.source } : { from: edge.source, to: edge.target });
const isDrawn = (edge: TopoEdge) => edge.kind !== "contains" && (edge.kind !== "runs-on" || edge.id === "runs-on:ollama>gpu-0");

// ---------------------------------------------------------------------------
// Visual state

interface Look {
  selected: boolean;
  related?: "up" | "down";
  effect?: Effect;
  root?: boolean;
  dim: boolean;
  /** Unrelated to the selection: softer than dim. */
  muted?: boolean;
  hidden: boolean;
}

interface CardData extends Record<string, unknown> {
  node: TopoNode;
  small: boolean;
  look: Look;
  rollup?: Rollup;
  count?: number;
  focused: boolean;
  onSelect: (id: string) => void;
  onToggle?: () => void;
}

interface FrameData extends Record<string, unknown> {
  node: TopoNode;
  rollup?: Rollup;
  look: Look;
  depth: number;
  onSelect: (id: string) => void;
  onToggle?: () => void;
}

interface EdgeData extends Record<string, unknown> {
  edge: TopoEdge;
  emphasis: "none" | "related" | "impact" | "dim" | "hidden";
  showLabel: boolean;
  centerY?: number;
}

const SIDES = [
  { id: "t", position: Position.Top, style: {} },
  { id: "b", position: Position.Bottom, style: {} },
  { id: "bl", position: Position.Bottom, style: { left: "28%" } },
  { id: "br", position: Position.Bottom, style: { left: "72%" } },
  { id: "l", position: Position.Left, style: {} },
  { id: "r", position: Position.Right, style: {} },
];
const HANDLE = "!size-px !min-h-0 !min-w-0 !border-0 !bg-transparent";

function Handles() {
  return (
    <>
      {SIDES.map((side) => (
        <Handle key={`s-${side.id}`} id={`s-${side.id}`} type="source" position={side.position} style={side.style} className={HANDLE} isConnectable={false} />
      ))}
      {SIDES.map((side) => (
        <Handle key={`t-${side.id}`} id={`t-${side.id}`} type="target" position={side.position} style={side.style} className={HANDLE} isConnectable={false} />
      ))}
    </>
  );
}

function lookClasses(look: Look) {
  return clsx(
    "transition-[opacity,box-shadow,border-color,background-color] duration-200",
    look.hidden && "pointer-events-none !opacity-[0.07]",
    !look.hidden && look.dim && "opacity-35",
    !look.hidden && !look.dim && look.muted && "opacity-60",
  );
}

function CardNode({ data }: NodeProps<Node<CardData>>) {
  const { node, look, small, rollup, count } = data;
  const health: Health = rollup ? rollup.health : node.health;
  const explained = node.tags.includes("fixture") || node.tags.includes("leftover");
  const inactive = health === "stopped" || health === "unknown";
  return (
    <div className={clsx("relative h-full w-full", lookClasses(look))}>
      <Handles />
      <button
        type="button"
        data-topo-id={node.id}
        tabIndex={data.focused ? 0 : -1}
        aria-pressed={look.selected}
        aria-label={`${node.name}, ${node.kindLabel}, ${HEALTH[health].word}, ${rollup ? `${count} pods` : node.status}`}
        onClick={() => data.onSelect(node.id)}
        className={clsx(
          "nodrag nopan pointer-events-auto grid h-full w-full cursor-pointer content-center gap-0.5 rounded-md border bg-surface px-2.5 text-left outline-none",
          explained || inactive ? "border-dashed" : "border-solid",
          look.effect || look.root ? "border-warn/70" : look.selected ? "border-accent" : look.related ? "border-fg-3" : "border-line-strong",
          look.effect === "down" && "bg-warn-soft",
          look.root && "border-2 bg-warn-soft",
          look.selected && "ring-2 ring-accent/45 ring-offset-0",
          "focus-visible:ring-2 focus-visible:ring-accent",
          inactive && !look.selected && "bg-surface/60",
        )}
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <NodeIcon node={node} className={clsx("size-3", look.selected ? "text-accent" : "text-fg-3")} />
          <span className={clsx("truncate font-mono", small ? "text-[11.5px]" : "text-[12px]", inactive ? "text-fg-2" : "text-fg")}>{node.name}</span>
          {node.active && <LiveDot className="ml-auto" />}
        </span>
        <span className="flex min-w-0 items-center gap-1.5 text-[11px] leading-4">
          <HealthMark health={health} size={9} />
          <span className={clsx("shrink-0", HEALTH_TEXT[health])}>{HEALTH_SHORT[health]}</span>
          {!small && <span className="truncate text-fg-3">· {rollup ? `${count} pods${rollup.explained.length ? `, ${rollup.explained.length} explained` : ""}` : node.status}</span>}
        </span>
      </button>
      {data.onToggle && (
        <button
          type="button"
          onClick={data.onToggle}
          aria-label={`Expand ${node.name}`}
          className="nodrag nopan pointer-events-auto absolute top-1 right-1 grid size-6 cursor-pointer place-items-center rounded text-fg-3 hover:bg-surface-2 hover:text-fg"
        >
          <Expand className="size-3" strokeWidth={2} />
        </button>
      )}
      {(look.effect || look.root) && (
        <span className="pointer-events-none absolute -top-2.5 left-2">
          {look.root ? <span className="inline-flex h-5 items-center rounded-[4px] border border-warn/60 bg-surface px-1.5 text-[11px] font-medium text-warn">Simulated failure</span> : <EffectChip effect={look.effect!} />}
        </span>
      )}
    </div>
  );
}

function FrameNode({ data }: NodeProps<Node<FrameData>>) {
  const { node, look, rollup, depth } = data;
  const lane = node.tags.includes("selected-lane");
  const health = rollup?.health ?? node.health;
  return (
    <div
      className={clsx(
        "h-full w-full rounded-lg border",
        lookClasses(look),
        look.root || look.effect ? "border-warn/60 border-dashed" : look.selected ? "border-accent" : lane ? "border-accent-line" : "border-line-strong",
        depth === 0 && "bg-surface/35",
        depth === 1 && "bg-surface/50",
        depth === 2 && "bg-surface/60",
        depth === 3 && "bg-surface-2/40",
      )}
    >
      <div className="flex h-7 max-w-full items-center gap-2 px-2.5">
        <button
          type="button"
          data-topo-id={node.id}
          tabIndex={-1}
          aria-pressed={look.selected}
          aria-label={`${node.name}, ${node.kindLabel}, ${HEALTH[health].word}`}
          onClick={() => data.onSelect(node.id)}
          className="nodrag nopan pointer-events-auto flex min-w-0 cursor-pointer items-center gap-1.5 rounded px-1 py-0.5 hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-accent"
        >
          <NodeIcon node={node} className={clsx("size-3", look.selected ? "text-accent" : "text-fg-3")} />
          <span className="label !text-[9.5px]">{node.kindLabel}</span>
          <span className="truncate font-mono text-[12px] text-fg">{node.name}</span>
        </button>
        <span className="pointer-events-none inline-flex items-center gap-1 text-[11px]">
          <HealthMark health={health} size={9} />
          <span className={HEALTH_TEXT[health]}>{HEALTH_SHORT[health]}</span>
          {rollup && rollup.explained.length > 0 && <span className="text-fg-3">· {rollup.explained.length} explained</span>}
        </span>
        {lane && <Tag tone="accent">Selected lane</Tag>}
        {(look.effect || look.root) && <span className="pointer-events-none">{look.root ? <Tag tone="warn">Simulated failure</Tag> : <EffectChip effect={look.effect!} />}</span>}
        {data.onToggle && (
          <button
            type="button"
            onClick={data.onToggle}
            aria-label={`Collapse ${node.name}`}
            className="nodrag nopan pointer-events-auto ml-auto grid size-6 cursor-pointer place-items-center rounded text-fg-3 hover:bg-surface-2 hover:text-fg"
          >
            <Shrink className="size-3" strokeWidth={2} />
          </button>
        )}
      </div>
    </div>
  );
}

function arrowHead(x: number, y: number, position: Position) {
  const s = 4.5;
  const l = 7;
  switch (position) {
    case Position.Top:
      return `M${x},${y} L${x - s},${y - l} L${x + s},${y - l} Z`;
    case Position.Bottom:
      return `M${x},${y} L${x - s},${y + l} L${x + s},${y + l} Z`;
    case Position.Left:
      return `M${x},${y} L${x - l},${y - s} L${x - l},${y + s} Z`;
    default:
      return `M${x},${y} L${x + l},${y - s} L${x + l},${y + s} Z`;
  }
}

const DASH: Record<TopoEdge["kind"], string | undefined> = {
  "depends-on": undefined,
  serves: undefined,
  "routes-to": "6 4",
  "runs-on": "1.5 4",
  contains: "2 3",
};

function TopoEdgeView({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps<Edge<EdgeData>>) {
  if (!data) return null;
  const { edge, emphasis, showLabel, centerY } = data;
  const aligned = Math.abs(sourceX - targetX) < 30 && (sourcePosition === Position.Bottom || sourcePosition === Position.Top);
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX: aligned ? sourceX : targetX,
    targetY,
    targetPosition,
    borderRadius: 10,
    offset: 12,
    centerY: aligned ? undefined : centerY,
  });
  const stroke = edge.broken
    ? "var(--fg-3)"
    : emphasis === "impact"
      ? "var(--warn)"
      : edge.active
        ? "var(--accent)"
        : emphasis === "related"
          ? "var(--fg-2)"
          : "var(--line-strong)";
  const opacity = emphasis === "hidden" ? 0.05 : emphasis === "dim" ? 0.25 : 1;
  const tipX = aligned ? sourceX : targetX;
  return (
    <>
      <path d={path} fill="none" stroke={stroke} strokeWidth={edge.active || emphasis === "impact" ? 1.75 : emphasis === "related" ? 1.5 : 1.25} strokeDasharray={edge.broken ? "2 4" : DASH[edge.kind]} strokeLinecap="round" opacity={opacity} style={{ transition: "opacity 200ms, stroke 200ms" }} />
      {edge.active && emphasis !== "hidden" && <path d={path} fill="none" stroke="var(--accent)" strokeWidth={2.25} strokeDasharray="2 10" strokeLinecap="round" className="topo-flow" opacity={opacity} />}
      <path d={arrowHead(tipX, targetY, targetPosition)} fill={stroke} opacity={opacity} />
      {showLabel && emphasis !== "hidden" && (
        <EdgeLabelRenderer>
          <div
            className={clsx(
              "nodrag nopan pointer-events-none absolute rounded-[4px] border bg-surface px-1.5 py-px font-mono text-[10.5px] whitespace-nowrap",
              emphasis === "impact" ? "border-warn/40 text-warn" : edge.active ? "border-accent-line text-accent" : "border-line-strong text-fg-2",
            )}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`, opacity }}
          >
            {edge.broken ? "no address" : edge.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

const nodeTypes = { card: CardNode, frame: FrameNode };
const edgeTypes = { topo: TopoEdgeView };

const reducedMotion = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// ---------------------------------------------------------------------------

interface ViewState {
  selected: string;
  whatIfOn: boolean;
  focus: boolean;
  filter: FilterId;
  query: string;
}

function useLooks(graph: TopologyGraph, view: ViewState, impact: WhatIf | undefined) {
  return useMemo(() => {
    const ups = new Set(upstream(graph, view.selected).map((l) => l.id));
    const downs = new Set(downstream(graph, view.selected).map((l) => l.id));
    const near = view.focus ? neighborhood(graph, view.selected, 1) : undefined;
    // Ancestors of anything visible stay visible as frames.
    if (near) {
      for (const id of [...near]) {
        let parent = graph.byId.get(id)?.parent;
        while (parent) {
          near.add(parent);
          parent = graph.byId.get(parent)?.parent;
        }
      }
    }
    const filtering = view.filter !== "all" || view.query.trim() !== "";
    const look = (id: string, isFrame: boolean): Look => {
      const node = graph.byId.get(id)!;
      const selected = id === view.selected;
      if (impact) {
        const hit = impact.byId.get(id);
        const root = id === impact.root;
        return { selected, root, effect: hit?.effect, dim: !root && !hit && !isFrame, hidden: !!near && !near.has(id) };
      }
      const related = ups.has(id) ? "up" : downs.has(id) ? "down" : undefined;
      const matches = matchesFilter(node, view.filter, view.query);
      return {
        selected,
        related,
        dim: filtering && !matches && !isFrame,
        muted: !filtering && !isFrame && !selected && !related,
        hidden: !!near && !near.has(id),
      };
    };
    return { look, ups, downs, near };
  }, [graph, view, impact]);
}

function GraphCanvas({ graph, view, setView, impact, collapsed, toggle }: { graph: TopologyGraph; view: ViewState; setView: (patch: Partial<ViewState>) => void; impact?: WhatIf; collapsed: Set<string>; toggle: (id: string) => void }) {
  const rf = useReactFlow();
  const wrapper = useRef<HTMLDivElement>(null);
  const layout = useMemo(() => layoutGraph(graph, collapsed), [graph, collapsed]);
  const { look, near } = useLooks(graph, view, impact);
  const select = useCallback((id: string) => setView({ selected: id }), [setView]);
  const shown = (id: string) => layout.proxy.get(id) ?? id;
  const focusTarget = shown(view.selected);

  const nodes = useMemo<Node[]>(() => {
    const frames: Node<FrameData>[] = layout.frames.map((f) => ({
      id: f.id,
      type: "frame",
      position: { x: f.x, y: f.y },
      width: f.w,
      height: f.h,
      zIndex: f.depth,
      selectable: false,
      draggable: false,
      focusable: false,
      data: { node: graph.byId.get(f.id)!, rollup: graph.rollups.get(f.id), look: look(f.id, true), depth: f.depth, onSelect: select, onToggle: f.collapsible ? () => toggle(f.id) : undefined },
    }));
    const cards: Node<CardData>[] = layout.cards.map((c) => {
      const node = graph.byId.get(c.id)!;
      const rollup = c.group ? graph.rollups.get(c.id) : undefined;
      const memberLooks = c.group ? (graph.children.get(c.id) ?? []).map((m) => look(m, false)) : [];
      const own = look(c.id, false);
      const merged: Look = c.group
        ? {
            ...own,
            selected: own.selected || layout.proxy.get(view.selected) === c.id,
            effect: own.effect ?? memberLooks.find((m) => m.effect)?.effect,
            related: own.related ?? memberLooks.find((m) => m.related)?.related,
            dim: own.dim && memberLooks.every((m) => m.dim),
            muted: own.muted && memberLooks.every((m) => m.muted || m.dim),
            hidden: own.hidden && memberLooks.every((m) => m.hidden),
          }
        : own;
      return {
        id: c.id,
        type: "card",
        position: { x: c.x, y: c.y },
        width: c.w,
        height: c.h,
        zIndex: 10,
        selectable: false,
        draggable: false,
        focusable: false,
        data: { node, small: !!c.small, look: merged, rollup, count: rollup?.total, focused: c.id === focusTarget, onSelect: select, onToggle: c.group ? () => toggle(c.id) : undefined },
      };
    });
    return [...frames, ...cards];
  }, [layout, graph, look, select, toggle, focusTarget, view.selected]);

  const edges = useMemo<Edge<EdgeData>[]>(() => {
    const seen = new Set<string>();
    const out: Edge<EdgeData>[] = [];
    const impactEdges = new Set(impact?.impacts.map((i) => i.edge.id));
    for (const edge of graph.edges.filter(isDrawn)) {
      const { from, to } = drawn(edge);
      const a = shown(from);
      const b = shown(to);
      if (a === b || !layout.rects.has(a) || !layout.rects.has(b)) continue;
      const key = `${a}>${b}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const route = ROUTES[key] ?? autoRoute(layout.rects.get(a)!, layout.rects.get(b)!);
      const touches = [from, to].includes(view.selected) || [a, b].includes(focusTarget);
      const hidden = near && !(near.has(from) && near.has(to));
      const emphasis: EdgeData["emphasis"] = hidden
        ? "hidden"
        : impact
          ? impactEdges.has(edge.id)
            ? "impact"
            : "dim"
          : touches
            ? "related"
            : edge.active
              ? "none"
              : view.filter !== "all" || view.query
                ? "dim"
                : "none";
      out.push({
        id: key,
        type: "topo",
        source: a,
        target: b,
        sourceHandle: `s-${route.s}`,
        targetHandle: `t-${route.t}`,
        zIndex: 5,
        selectable: false,
        focusable: false,
        data: { edge, emphasis, showLabel: emphasis === "impact" || emphasis === "related" || edge.active || !!edge.broken, centerY: route.lane !== undefined ? layout.channelY + route.lane : undefined },
      });
    }
    return out;
  }, [graph, layout, view, impact, near, focusTarget]);

  // Fit once the nodes are measured, and again when the canvas is resized.
  const initialized = useNodesInitialized();
  const fitted = useRef(false);
  useEffect(() => {
    const el = wrapper.current;
    if (!initialized || fitted.current || !el?.clientWidth || !el.clientHeight) return;
    fitted.current = true;
    void rf.fitView({ padding: FIT_PADDING, maxZoom: 1.1 });
  }, [initialized, rf]);
  useEffect(() => {
    const el = wrapper.current;
    if (!el) return;
    let size = [el.clientWidth, el.clientHeight];
    const observer = new ResizeObserver(() => {
      if (Math.abs(el.clientWidth - size[0]) < 24 && Math.abs(el.clientHeight - size[1]) < 24) return;
      size = [el.clientWidth, el.clientHeight];
      fitted.current = true;
      void rf.fitView({ padding: FIT_PADDING, maxZoom: 1.1 });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [rf]);

  // Refit when the shape of the graph changes (expand, collapse, focus).
  const shapeKey = `${[...collapsed].sort().join(",")}|${view.focus ? view.selected : ""}`;
  const firstFit = useRef(true);
  useEffect(() => {
    if (firstFit.current) {
      firstFit.current = false;
      return;
    }
    const frame = requestAnimationFrame(() => {
      // Fit the neighborhood's cards, not the frames kept around them for context.
      const frames = new Set(layout.frames.map((f) => f.id));
      const core = view.focus ? [...neighborhood(graph, view.selected, 1)] : undefined;
      const visible = core ? [...new Set(core.map(shown))].filter((id) => layout.rects.has(id) && (!frames.has(id) || id === view.selected)) : undefined;
      void rf.fitView({ padding: view.focus ? 0.25 : FIT_PADDING, maxZoom: 1.2, duration: reducedMotion() ? 0 : 280, nodes: visible?.map((id) => ({ id })) });
    });
    return () => cancelAnimationFrame(frame);
  }, [shapeKey]);

  // Keyboard: arrows move between components spatially; f focus, w what-if, Escape clears.
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const keys: Record<string, [number, number]> = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] };
    if (keys[event.key]) {
      event.preventDefault();
      const [dx, dy] = keys[event.key];
      const current = layout.rects.get(focusTarget);
      if (!current) return;
      const anchor = (r: Rect, id: string) => (layout.frames.some((f) => f.id === id) ? { x: r.x + 80, y: r.y + 14 } : { x: r.x + r.w / 2, y: r.y + r.h / 2 });
      const from = anchor(current, focusTarget);
      let best: { id: string; score: number } | undefined;
      for (const [id, rect] of layout.rects) {
        if (id === focusTarget || (near && !near.has(id) && ![...near].some((n) => shown(n) === id))) continue;
        const to = anchor(rect, id);
        const along = (to.x - from.x) * dx + (to.y - from.y) * dy;
        if (along <= 4) continue;
        const across = Math.abs((to.x - from.x) * dy) + Math.abs((to.y - from.y) * dx);
        const score = along + across * 2.2;
        if (!best || score < best.score) best = { id, score };
      }
      if (best) {
        setView({ selected: best.id });
        wrapper.current?.querySelector<HTMLElement>(`[data-topo-id="${CSS.escape(best.id)}"]`)?.focus({ preventScroll: true });
      }
    } else if (event.key === "f") setView({ focus: !view.focus });
    else if (event.key === "w") setView({ whatIfOn: !view.whatIfOn });
    else if (event.key === "Escape") setView({ whatIfOn: false, focus: false });
  };

  const button = "grid size-7 cursor-pointer place-items-center rounded-[4px] text-fg-2 hover:bg-surface-2 hover:text-fg aria-pressed:bg-accent-soft aria-pressed:text-accent";
  const zoomOpts = { duration: reducedMotion() ? 0 : 200 };

  return (
    <div
      ref={wrapper}
      onKeyDown={onKeyDown}
      role="group"
      aria-label="Dependency graph. Arrow keys move between components, W shows what fails, F focuses the neighborhood, Escape clears."
      className="relative h-full w-full"
    >
      <style>{`@keyframes topo-flow{to{stroke-dashoffset:-24}}@media (prefers-reduced-motion:no-preference){.topo-flow{animation:topo-flow .9s linear infinite}}`}</style>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: FIT_PADDING, maxZoom: 1.1 }}
        minZoom={0.3}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elementsSelectable={false}
        disableKeyboardA11y
        zoomOnDoubleClick={false}
        proOptions={{ hideAttribution: true }}
        style={{ background: "var(--bg)" }}
      >
        <Background gap={20} size={1} color="var(--grid)" />
        <Panel position="top-right" className="!m-2 flex items-center gap-0.5 rounded-md border border-line bg-surface p-0.5">
          <button type="button" className={button} aria-label="Zoom in" onClick={() => void rf.zoomIn(zoomOpts)}>
            <Plus className="size-3.5" strokeWidth={2} />
          </button>
          <button type="button" className={button} aria-label="Zoom out" onClick={() => void rf.zoomOut(zoomOpts)}>
            <Minus className="size-3.5" strokeWidth={2} />
          </button>
          <button type="button" className={button} aria-label="Fit the graph" onClick={() => void rf.fitView({ padding: FIT_PADDING, maxZoom: 1.1, ...zoomOpts })}>
            <Scan className="size-3.5" strokeWidth={2} />
          </button>
          <span className="mx-0.5 h-4 w-px bg-line" />
          <button type="button" className={button} aria-label="Focus on the selected component's neighborhood" aria-pressed={view.focus} onClick={() => setView({ focus: !view.focus })}>
            <Focus className="size-3.5" strokeWidth={2} />
          </button>
        </Panel>
        <Panel position="bottom-left" className="!m-2">
          <Legend />
        </Panel>
      </ReactFlow>
    </div>
  );
}

const FIT_PADDING = { top: "24px", right: "20px", bottom: "44px", left: "20px" } as const;

function Legend() {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-md border border-line bg-surface/95 text-[11px] backdrop-blur-sm">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex h-7 cursor-pointer items-center gap-2 px-2.5 text-fg-2 hover:text-fg">
        <span className="flex items-center gap-1">
          {(["healthy", "degraded", "failing", "expected-broken", "leftover", "stopped", "unknown"] as Health[]).map((h) => (
            <HealthMark key={h} health={h} size={9} />
          ))}
        </span>
        Legend
      </button>
      {open && (
        <div className="grid gap-2 border-t border-line px-2.5 py-2">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {(["healthy", "degraded", "failing", "expected-broken", "leftover", "stopped", "unknown"] as Health[]).map((h) => (
              <span key={h} className={clsx("inline-flex items-center gap-1.5", HEALTH_TEXT[h])}>
                <HealthMark health={h} size={9} />
                {HEALTH[h].word}
              </span>
            ))}
          </div>
          <div className="grid gap-1 border-t border-line pt-2 text-fg-2">
            {(["depends-on", "serves", "routes-to", "runs-on"] as const).map((kind) => (
              <span key={kind} className="inline-flex items-center gap-2">
                <svg width="28" height="6" aria-hidden>
                  <line x1="0" y1="3" x2="28" y2="3" stroke="var(--fg-3)" strokeWidth="1.5" strokeDasharray={DASH[kind]} strokeLinecap="round" />
                </svg>
                {EDGE_KIND[kind].word}
              </span>
            ))}
            <span className="inline-flex items-center gap-2">
              <svg width="28" height="6" aria-hidden>
                <line x1="0" y1="3" x2="28" y2="3" stroke="var(--accent)" strokeWidth="2" />
              </svg>
              Traffic now
            </span>
            <span className="text-fg-3">Nesting shows what contains or runs what.</span>
          </div>
        </div>
      )}
    </div>
  );
}

const ZONES: { label: string; ids: (graph: TopologyGraph) => string[] }[] = [
  { label: "Operator and services", ids: () => ["operator", "worker", "rag", "pgvector", "ollama", "openai"] },
  { label: "Host", ids: () => ["host", "gpu-0", "gpu-1", "docker"] },
  { label: "Lane minh-lane", ids: (g) => ["profile:minh-lane", "node:minh-lane", "ns:default", ...(g.children.get("ns:default") ?? []), "ns:kube-system", ...(g.children.get("ns:kube-system") ?? [])] },
  { label: "Other profiles", ids: () => OTHER_PROFILES },
];

function ListView({ graph, view, setView, impact, inline }: { graph: TopologyGraph; view: ViewState; setView: (patch: Partial<ViewState>) => void; impact?: WhatIf; inline: ReactNode }) {
  const { look } = useLooks(graph, { ...view, focus: false }, impact);
  return (
    <div className="grid gap-3">
      {ZONES.map((zone) => {
        const nodes = zone
          .ids(graph)
          .map((id) => graph.byId.get(id))
          .filter((n): n is TopoNode => !!n && matchesFilter(n, view.filter, view.query));
        if (!nodes.length) return null;
        return (
          <section key={zone.label} className="overflow-hidden rounded-lg border border-line bg-surface">
            <h3 className="label border-b border-line px-3 py-2 !text-[10px]">{zone.label}</h3>
            <ul className="divide-y divide-line">
              {nodes.map((node) => {
                const l = look(node.id, false);
                const indent = node.kind === "pod" || node.kind === "service" || node.kind === "endpoints" ? "pl-7" : node.kind === "namespace" || node.kind === "k8s-node" ? "pl-5" : "";
                return (
                  <li key={node.id}>
                    <button
                      type="button"
                      aria-pressed={l.selected}
                      onClick={() => setView({ selected: node.id })}
                      className={clsx("grid w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-3 py-2 text-left", indent, l.selected ? "bg-accent-soft" : "hover:bg-surface-2", impact && l.dim && "opacity-45")}
                    >
                      <span className="grid min-w-0 gap-0.5">
                        <span className="flex min-w-0 items-center gap-1.5">
                          <NodeIcon node={node} className="size-3 text-fg-3" />
                          <span className="truncate font-mono text-[12.5px] text-fg">{node.name}</span>
                          {node.active && <LiveDot />}
                        </span>
                        <span className="flex min-w-0 items-center gap-1.5 text-[11.5px]">
                          <HealthMark health={node.health} size={9} />
                          <span className={HEALTH_TEXT[node.health]}>{HEALTH_SHORT[node.health]}</span>
                          <span className="truncate text-fg-3">· {node.status}</span>
                        </span>
                      </span>
                      {l.effect ? <EffectChip effect={l.effect} /> : l.root ? <Tag tone="warn">Simulated</Tag> : null}
                    </button>
                    {l.selected && <div className="border-t border-accent-line bg-bg/40 xl:hidden">{inline}</div>}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function usePhone() {
  const query = "(max-width: 767px)";
  const [phone, setPhone] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const sync = () => setPhone(media.matches);
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);
  return phone;
}

export default function DependencyGraph() {
  const { graph } = useGraph();
  const phone = usePhone();
  const [mode, setMode] = useState<"graph" | "list" | null>(null);
  const [view, setViewState] = useState<ViewState>({ selected: "worker", whatIfOn: false, focus: false, filter: "all", query: "" });
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set(["ns:kube-system"]));
  const setView = useCallback((patch: Partial<ViewState>) => setViewState((current) => ({ ...current, ...patch })), []);
  const toggle = useCallback((id: string) => {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);
  const impact = useMemo(() => (graph && view.whatIfOn ? whatIf(graph, view.selected) : undefined), [graph, view.whatIfOn, view.selected]);
  if (!graph) return <StageFallback />;
  const shownMode = mode ?? (phone ? "list" : "graph");

  const inspector = (
    <Inspector
      graph={graph}
      id={view.selected}
      onSelect={(id) => setView({ selected: id })}
      whatIfOn={view.whatIfOn}
      onWhatIf={(whatIfOn) => setView({ whatIfOn })}
      impact={impact}
      footer={
        <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <button
            type="button"
            aria-pressed={view.focus}
            onClick={() => {
              setMode("graph");
              setView({ focus: !view.focus });
            }}
            className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12px] text-fg-2 hover:bg-surface-2 hover:text-fg aria-pressed:border-accent-line aria-pressed:bg-accent-soft aria-pressed:text-accent"
          >
            <Focus className="size-3.5" strokeWidth={2} /> {view.focus ? "Show everything" : "Focus neighborhood"}
          </button>
          <span className="hidden text-[11.5px] text-fg-3 md:inline">Arrows move · W what-if · F focus · Esc clears</span>
        </div>
      }
    />
  );

  const onQuery = (query: string) => {
    const match = query.trim() ? graph.nodes.find((n) => matchesFilter(n, "all", query)) : undefined;
    setView(match ? { query, selected: match.id } : { query });
  };

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <DemoTag />
          <LaneHealth graph={graph} />
        </div>
        <div className="flex items-center gap-2">
          <Segmented
            label="View"
            value={shownMode}
            onChange={(next) => setMode(next)}
            options={[
              { value: "graph", label: <><Network className="size-3.5" strokeWidth={1.75} /> Graph</> },
              { value: "list", label: <><List className="size-3.5" strokeWidth={1.75} /> List</> },
            ]}
          />
        </div>
      </div>
      <FilterBar graph={graph} filter={view.filter} onFilter={(filter) => setView({ filter })} query={view.query} onQuery={onQuery} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        {shownMode === "graph" ? (
          <div className="flex h-[460px] flex-col overflow-hidden rounded-lg border border-line md:h-[700px]">
            <div className="border-b border-line bg-surface px-3 py-2">
              <TrafficLine graph={graph} compact />
            </div>
            <div className="min-h-0 flex-1">
              <ReactFlowProvider>
                <GraphCanvas graph={graph} view={view} setView={setView} impact={impact} collapsed={collapsed} toggle={toggle} />
              </ReactFlowProvider>
            </div>
          </div>
        ) : (
          <ListView graph={graph} view={view} setView={setView} impact={impact} inline={inspector} />
        )}
        <aside className={clsx("min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface xl:sticky xl:top-20 xl:block xl:max-h-[700px] xl:overflow-y-auto", shownMode === "list" && "hidden")}>
          {inspector}
        </aside>
      </div>
      <p className="text-[12px] leading-relaxed text-fg-3">
        Demo state shaped by the lab survey (Nov 1, 2026). Arrows point from a caller to what it needs; nesting shows what contains or runs what. Traffic follows the demo campaign's current phase. Health here is the lab's state, not a benchmark outcome.
      </p>
    </div>
  );
}
