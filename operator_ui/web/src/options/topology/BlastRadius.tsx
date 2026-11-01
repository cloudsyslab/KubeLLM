import clsx from "clsx";
import { ArrowLeft, Crosshair } from "lucide-react";
import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Tip } from "@/components/ui";
import { downstream, HEALTH, upstream, whatIf, type Effect, type TopoEdge, type TopologyGraph, type WhatIf } from "@/demo/topologyGraph";
import { StageFallback } from "../OptionsRoom";
import { DemoTag, EffectChip, HEALTH_SHORT, HEALTH_TEXT, HealthBadge, HealthMark, Inspector, LaneHealth, LiveDot, NodeIcon, TrafficLine, useGraph, WhatIfPanel, WhatIfToggle } from "./shared";

// Ego-centric lineage: the selected component in the middle, what it needs
// fanning out to the left by hop distance, and what fails with it fanning out
// to the right. Clicking anything re-centers on it, so exploring is walking.

const MAX = 3;
const LIMIT = 6;
// Phones stack the lineage: the center first, then closest-first on each side.
const UP_ORDER = ["order-2", "order-3", "order-4"];
const DOWN_ORDER = ["order-5", "order-6", "order-7"];

interface Hop {
  id: string;
  depth: number;
  /** The node one hop closer to the center. */
  next: string;
  edge: TopoEdge;
  effect?: Effect;
  reason?: string;
}

function trace(graph: TopologyGraph, center: string, impact?: WhatIf) {
  const up = new Map<string, Hop>();
  const queue = [center];
  const depth = new Map([[center, 0]]);
  while (queue.length) {
    const current = queue.shift()!;
    for (const link of upstream(graph, current)) {
      if (depth.has(link.id)) continue;
      depth.set(link.id, depth.get(current)! + 1);
      up.set(link.id, { id: link.id, depth: depth.get(link.id)!, next: current, edge: link.edge });
      queue.push(link.id);
    }
  }
  const down = new Map<string, Hop>();
  if (impact) {
    for (const i of impact.impacts) down.set(i.id, { id: i.id, depth: i.depth, next: i.via, edge: i.edge, effect: i.effect, reason: i.reason });
  } else {
    const seen = new Map([[center, 0]]);
    const q = [center];
    while (q.length) {
      const current = q.shift()!;
      for (const link of downstream(graph, current)) {
        if (seen.has(link.id)) continue;
        seen.set(link.id, seen.get(current)! + 1);
        down.set(link.id, { id: link.id, depth: seen.get(link.id)!, next: current, edge: link.edge });
        q.push(link.id);
      }
    }
  }
  return { up, down };
}

/** Columns 1..MAX, the last holding everything farther; each sorted to follow its parent column. */
function columnsOf(hops: Map<string, Hop>, graph: TopologyGraph) {
  const cols: Hop[][] = Array.from({ length: MAX }, () => []);
  for (const hop of hops.values()) cols[Math.min(hop.depth, MAX) - 1].push(hop);
  const order = new Map<string, number>();
  cols.forEach((col, c) => {
    col.sort((a, b) => {
      const pa = c === 0 ? 0 : (order.get(a.next) ?? 999);
      const pb = c === 0 ? 0 : (order.get(b.next) ?? 999);
      return pa - pb || a.depth - b.depth || HEALTH[graph.byId.get(a.id)!.health].rank - HEALTH[graph.byId.get(b.id)!.health].rank || graph.byId.get(a.id)!.name.localeCompare(graph.byId.get(b.id)!.name);
    });
    col.forEach((hop, i) => order.set(hop.id, i));
  });
  return cols;
}

function Chip({ graph, hop, side, onPick, onHover, lit }: { graph: TopologyGraph; hop: Hop; side: "up" | "down"; onPick: (id: string) => void; onHover: (key: string | null) => void; lit: boolean }) {
  const node = graph.byId.get(hop.id)!;
  const key = `${side}:${hop.id}`;
  const rollup = graph.rollups.get(hop.id);
  const health = rollup?.health ?? node.health;
  return (
    <Tip side={side === "up" ? "left" : "right"} content={<span>{hop.reason ?? `${side === "up" ? "Needed" : "Needs it"}: ${hop.edge.label}. ${hop.edge.impact}`}</span>}>
      <button
        type="button"
        data-chip={key}
        onClick={() => onPick(hop.id)}
        onMouseEnter={() => onHover(key)}
        onMouseLeave={() => onHover(null)}
        onFocus={() => onHover(key)}
        onBlur={() => onHover(null)}
        className={clsx(
          "grid w-full cursor-pointer gap-1 rounded-md border bg-surface px-2.5 py-2 text-left transition-colors",
          hop.effect === "down" ? "border-warn/60 bg-warn-soft" : hop.effect === "impaired" ? "border-warn/40" : lit ? "border-fg-3" : "border-line-strong hover:border-fg-3",
        )}
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <NodeIcon node={node} className="size-3 text-fg-3" />
          <span className="truncate text-[12.5px] text-fg">{node.name}</span>
          {node.active && <LiveDot />}
          {hop.depth > MAX && <span className="num ml-auto shrink-0 text-[10.5px] text-fg-3">{hop.depth} hops</span>}
        </span>
        <span className="flex min-w-0 items-center justify-between gap-2">
          <span className={clsx("inline-flex min-w-0 items-center gap-1.5 text-[11.5px]", HEALTH_TEXT[health])}>
            <HealthMark health={health} size={9} />
            <span className="truncate">{HEALTH_SHORT[health]}</span>
          </span>
          {hop.effect ? <EffectChip effect={hop.effect} /> : <span className="truncate font-mono text-[10.5px] text-fg-3">{hop.edge.label}</span>}
        </span>
      </button>
    </Tip>
  );
}

interface Wire {
  key: string;
  d: string;
  tone: "up" | "down" | "impaired" | "outcome" | "active";
}

export default function BlastRadius() {
  const { graph } = useGraph();
  const [history, setHistory] = useState<string[]>(["pgvector"]);
  const [whatIfOn, setWhatIfOn] = useState(true);
  const [hovered, setHovered] = useState<string | null>(null);
  const [wires, setWires] = useState<Wire[]>([]);
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const stage = useRef<HTMLDivElement>(null);
  const center = history[history.length - 1];

  const impact = useMemo(() => (graph && whatIfOn ? whatIf(graph, center) : undefined), [graph, whatIfOn, center]);
  const lineage = useMemo(() => (graph ? trace(graph, center, impact) : undefined), [graph, center, impact]);
  const trim = (cols: Hop[][]) => cols.slice(0, Math.max(1, cols.reduce((last, col, i) => (col.length ? i + 1 : last), 0)));
  const upCols = useMemo(() => (graph && lineage ? trim(columnsOf(lineage.up, graph)) : []), [graph, lineage]);
  const downCols = useMemo(() => (graph && lineage ? trim(columnsOf(lineage.down, graph)) : []), [graph, lineage]);

  const pick = useCallback((id: string) => {
    setHovered(null);
    setOpened(new Set());
    setHistory((h) => (h[h.length - 1] === id ? h : [...h.slice(-11), id]));
  }, []);

  // The chain from a hovered chip back to the center lights up.
  const litKeys = useMemo(() => {
    const lit = new Set<string>();
    if (!hovered || !lineage) return lit;
    const [side, id] = hovered.split(/:(.*)/s);
    const map = side === "up" ? lineage.up : lineage.down;
    let current: string | undefined = id;
    while (current && current !== center) {
      lit.add(`${side}:${current}`);
      current = map.get(current)?.next;
    }
    return lit;
  }, [hovered, lineage, center]);

  // Wires are drawn from measured chip positions.
  useLayoutEffect(() => {
    const root = stage.current;
    if (!root || !lineage) return;
    const measure = () => {
      if (getComputedStyle(root).flexDirection === "column") {
        setWires((w) => (w.length ? [] : w));
        return;
      }
      const box = root.getBoundingClientRect();
      const rect = (key: string) => root.querySelector<HTMLElement>(`[data-chip="${CSS.escape(key)}"]`)?.getBoundingClientRect();
      const next: Wire[] = [];
      for (const [side, map] of [["up", lineage.up], ["down", lineage.down]] as const) {
        for (const hop of map.values()) {
          if (Math.min(hop.depth, MAX) === Math.min(map.get(hop.next)?.depth ?? 0, MAX) && hop.next !== center) continue;
          const far = rect(`${side}:${hop.id}`);
          const near = rect(hop.next === center ? "center" : `${side}:${hop.next}`);
          if (!far || !near) continue;
          const [ax, ay, bx, by] =
            side === "up"
              ? [far.right - box.left, far.top + far.height / 2 - box.top, near.left - box.left, near.top + near.height / 2 - box.top]
              : [near.right - box.left, near.top + near.height / 2 - box.top, far.left - box.left, far.top + far.height / 2 - box.top];
          const mid = (ax + bx) / 2;
          next.push({
            key: `${side}:${hop.id}`,
            d: `M${ax},${ay} C${mid},${ay} ${mid},${by} ${bx},${by}`,
            tone: hop.edge.active ? "active" : side === "up" ? "up" : !whatIfOn ? "up" : hop.effect === "impaired" ? "impaired" : hop.effect === "outcome" ? "outcome" : "down",
          });
        }
      }
      setWires((current) => (JSON.stringify(current) === JSON.stringify(next) ? current : next));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    return () => observer.disconnect();
  }, [lineage, center, upCols, downCols, whatIfOn, opened]);

  if (!graph || !lineage) return <StageFallback />;
  const node = graph.byId.get(center);
  const counts = { down: 0, impaired: 0, outcome: 0 };
  for (const hop of lineage.down.values()) if (hop.effect) counts[hop.effect] += 1;

  const column = (hops: Hop[], side: "up" | "down", c: number) => (
    <div key={`${side}-${c}`} className={clsx("grid min-w-0 flex-1 content-center gap-2 md:order-none md:min-w-[136px] md:max-w-[220px]", (side === "up" ? UP_ORDER : DOWN_ORDER)[c], hops.length === 0 && "hidden md:grid")}>
      <div className={clsx("label !text-[10px]", side === "up" ? "md:text-right" : "")}>
        <span className="md:hidden">{side === "up" ? "Needs" : whatIfOn ? "If it fails" : "Needed by"} · </span>
        {c + 1 === MAX ? `${MAX}+ hops` : `${c + 1} ${c === 0 ? "hop" : "hops"}`}
      </div>
      {hops.length ? (
        <>
          {(opened.has(`${side}-${c}`) ? hops : hops.slice(0, LIMIT)).map((hop) => (
            <Chip key={hop.id} graph={graph} hop={hop} side={side} onPick={pick} onHover={setHovered} lit={litKeys.has(`${side}:${hop.id}`)} />
          ))}
          {hops.length > LIMIT && (
            <button
              type="button"
              aria-expanded={opened.has(`${side}-${c}`)}
              onClick={() =>
                setOpened((current) => {
                  const next = new Set(current);
                  if (next.has(`${side}-${c}`)) next.delete(`${side}-${c}`);
                  else next.add(`${side}-${c}`);
                  return next;
                })
              }
              className="h-8 cursor-pointer rounded-md border border-dashed border-line-strong text-[12px] text-fg-2 hover:text-fg"
            >
              {opened.has(`${side}-${c}`) ? "Show fewer" : `${hops.length - LIMIT} more`}
            </button>
          )}
        </>
      ) : (
        <div className="grid h-14 place-items-center rounded-md border border-dashed border-line px-2 text-center text-[11.5px] text-fg-3">{side === "up" ? "Needs nothing" : whatIfOn ? "Nothing fails with it" : "Nothing needs it"}</div>
      )}
    </div>
  );

  const quick = ["pgvector", "docker", "sys:kube-apiserver", "ollama", "openai", "host", "pod:curl-pod", "fixture:pod"].filter((id) => graph.byId.has(id));

  return (
    <div className="grid gap-3">
      <div className="grid gap-2 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <DemoTag />
          <LaneHealth graph={graph} />
        </div>
        <TrafficLine graph={graph} />
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <button
          type="button"
          onClick={() => setHistory((h) => (h.length > 1 ? h.slice(0, -1) : h))}
          disabled={history.length < 2}
          className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg disabled:cursor-default disabled:opacity-40"
        >
          <ArrowLeft className="size-3.5" strokeWidth={2} /> Back
        </button>
        <nav aria-label="Exploration trail" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-[12.5px]">
          {history.slice(-6).map((id, i, list) => (
            <span key={`${id}-${i}`} className="inline-flex shrink-0 items-center gap-1">
              {i > 0 && <span className="text-fg-3">›</span>}
              <span className={i === list.length - 1 ? "text-fg" : "text-fg-3"}>{graph.byId.get(id)?.name ?? id}</span>
            </span>
          ))}
        </nav>
        <div className="flex max-w-full items-center gap-1 overflow-x-auto" role="group" aria-label="Start from">
          <span className="mr-1 shrink-0 text-[12px] text-fg-3">Try</span>
          {quick.map((id) => (
            <button
              key={id}
              type="button"
              aria-pressed={id === center}
              onClick={() => pick(id)}
              className={clsx("h-7 shrink-0 cursor-pointer rounded-md border px-2 text-[12px] transition-colors", id === center ? "border-accent-line bg-accent-soft text-accent" : "border-line text-fg-2 hover:text-fg")}
            >
              {graph.byId.get(id)!.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4">
        <section className="min-w-0 rounded-lg border border-line bg-surface">
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5 text-[12.5px]">
            <span className="text-fg-2">
              <span className="text-fg">Needs</span> {lineage.up.size} upstream
            </span>
            <span className="text-fg-2">
              {whatIfOn ? (
                <>
                  <span className="text-fg">If it fails</span> {lineage.down.size} affected
                  {lineage.down.size > 0 && <span className="text-fg-3"> · {[counts.down && `${counts.down} down`, counts.impaired && `${counts.impaired} impaired`, counts.outcome && `${counts.outcome} outcome`].filter(Boolean).join(", ")}</span>}
                </>
              ) : (
                <>
                  <span className="text-fg">Needed by</span> {lineage.down.size} downstream
                </>
              )}
            </span>
          </header>
          <div className="overflow-x-auto">
          <div ref={stage} className="relative flex flex-col gap-5 p-4 md:min-w-max md:flex-row md:items-stretch md:justify-center md:gap-7">
            <svg className="pointer-events-none absolute inset-0 hidden h-full w-full md:block" aria-hidden>
              {wires.map((wire) => {
                const lit = litKeys.has(wire.key);
                const stroke = wire.tone === "active" ? "var(--accent)" : wire.tone === "up" ? "var(--fg-3)" : wire.tone === "outcome" ? "var(--fg-3)" : "var(--warn)";
                return (
                  <path
                    key={wire.key}
                    d={wire.d}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={lit ? 2 : wire.tone === "active" ? 1.75 : 1.25}
                    strokeDasharray={wire.tone === "impaired" ? "5 4" : wire.tone === "outcome" ? "1.5 4" : undefined}
                    strokeLinecap="round"
                    opacity={hovered && !lit ? 0.25 : wire.tone === "up" ? 0.7 : 0.9}
                    style={{ transition: "opacity 150ms" }}
                  />
                );
              })}
            </svg>
            {upCols
              .map((hops, c) => ({ hops, c }))
              .reverse()
              .map(({ hops, c }) => column(hops, "up", c))}
            <div className="relative order-first grid min-w-0 shrink-0 content-center md:order-none md:w-[230px]">
              <div data-chip="center" className="grid gap-2 rounded-lg border-2 border-accent bg-surface p-3">
                {node ? (
                  <>
                    <div className="flex items-center gap-1.5">
                      <Crosshair className="size-3.5 text-accent" strokeWidth={2} aria-hidden />
                      <span className="label !text-[10px]">{node.kindLabel}</span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <NodeIcon node={node} className="mt-[3px] text-fg-3" />
                      <span className="min-w-0 font-mono text-[13.5px] leading-snug font-medium break-all text-fg">{node.name}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px]">
                      <HealthBadge health={graph.rollups.get(center)?.health ?? node.health} />
                      <span className="flex min-w-0 items-center gap-1.5 text-fg-3">
                        {node.active && <LiveDot />}
                        <span className="truncate">{node.status}</span>
                      </span>
                    </div>
                    <p className="text-[12px] leading-snug text-fg-2">{node.reason}</p>
                    <WhatIfToggle on={whatIfOn} onChange={setWhatIfOn} className="w-full" />
                  </>
                ) : (
                  <p className="text-[12.5px] text-fg-3">Not present at this moment of the replay.</p>
                )}
              </div>
            </div>
            {downCols.map((hops, c) => column(hops, "down", c))}
          </div>
          </div>
          <footer className="flex flex-wrap gap-x-5 gap-y-1 border-t border-line px-4 py-2.5 text-[11.5px] text-fg-3">
            <span className="inline-flex items-center gap-2">
              <svg width="24" height="6" aria-hidden>
                <line x1="0" y1="3" x2="24" y2="3" stroke="var(--fg-3)" strokeWidth="1.5" />
              </svg>
              Needs
            </span>
            <span className="inline-flex items-center gap-2">
              <svg width="24" height="6" aria-hidden>
                <line x1="0" y1="3" x2="24" y2="3" stroke="var(--warn)" strokeWidth="1.5" />
              </svg>
              Goes down
            </span>
            <span className="inline-flex items-center gap-2">
              <svg width="24" height="6" aria-hidden>
                <line x1="0" y1="3" x2="24" y2="3" stroke="var(--warn)" strokeWidth="1.5" strokeDasharray="5 4" />
              </svg>
              Impaired
            </span>
            <span className="inline-flex items-center gap-2">
              <svg width="24" height="6" aria-hidden>
                <line x1="0" y1="3" x2="24" y2="3" stroke="var(--accent)" strokeWidth="2" />
              </svg>
              Traffic now
            </span>
            <span>Click any component to re-center on it. Hover to trace its path.</span>
          </footer>
        </section>
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="min-w-0 self-start rounded-lg border border-line bg-surface">
            <header className="border-b border-line px-4 py-2.5">
              <h3 className="text-[13px] font-medium">{whatIfOn ? "Why each fails" : "Impact report"}</h3>
              <p className="text-[12px] text-fg-3">{whatIfOn ? "Simulated. Nothing is stopped." : "Turn on the simulated failure to see what goes down and why."}</p>
            </header>
            <div className="p-4">
              {impact ? (
                <WhatIfPanel graph={graph} impact={impact} onSelect={pick} />
              ) : (
                <WhatIfToggle on={whatIfOn} onChange={setWhatIfOn} />
              )}
            </div>
          </section>
          <aside className="min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface">
            <Inspector graph={graph} id={center} onSelect={pick} whatIfOn={whatIfOn} onWhatIf={setWhatIfOn} impact={impact} hideWhatIf />
          </aside>
        </div>
      </div>
      <p className="text-[12px] leading-relaxed text-fg-3">
        Demo state shaped by the lab survey (Nov 1, 2026). A simulated failure takes down what runs on or inside it and what can't work without it; soft dependencies are only impaired. Fixture and leftover failures are benchmark context, not lab faults.
      </p>
    </div>
  );
}
