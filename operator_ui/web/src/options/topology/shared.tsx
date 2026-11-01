import clsx from "clsx";
import {
  AppWindow,
  ArrowRight,
  Bot,
  Box,
  Boxes,
  Cloud,
  Container,
  Cpu,
  Database,
  FlaskConical,
  Folder,
  Layers,
  Microchip,
  Route,
  Search,
  Server,
  Terminal,
  TriangleAlert,
  Waypoints,
  X,
  type LucideIcon,
} from "lucide-react";
import { useMemo, type ReactNode } from "react";
import { Tag, Tip } from "@/components/ui";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import {
  changesFor,
  downstream,
  EDGE_KIND,
  EFFECT,
  graphAt,
  HEALTH,
  upstream,
  type Effect,
  type Health,
  type Link,
  type TopoNode,
  type TopologyGraph,
  type WhatIf,
} from "@/demo/topologyGraph";

/** The lab graph at the shared replay moment, recomputed once per replay second. */
export function useGraph() {
  const { campaign, t } = useReplay();
  const second = Math.floor(t);
  const graph = useMemo(() => (campaign ? graphAt(campaign, second) : undefined), [campaign, second]);
  return { graph, campaign, t: second };
}

// Health is an operator state, never a Ground Truth outcome: neutral for
// healthy, amber for degraded or failing, outlined for stopped and unknown, a
// half mark for fixtures that are broken by design.
export const HEALTH_SHORT: Record<Health, string> = {
  healthy: "Healthy",
  degraded: "Degraded",
  failing: "Failing",
  "expected-broken": "Expected",
  leftover: "Leftover",
  stopped: "Stopped",
  unknown: "Unknown",
};

export const HEALTH_TEXT: Record<Health, string> = {
  healthy: "text-fg-2",
  degraded: "text-warn",
  failing: "text-warn font-medium",
  "expected-broken": "text-fg-2",
  leftover: "text-fg-2",
  stopped: "text-fg-3",
  unknown: "text-fg-3",
};

export function HealthMark({ health, size = 10, className }: { health: Health; size?: number; className?: string }) {
  const props = { width: size, height: size, viewBox: "0 0 10 10", "aria-hidden": true, className: clsx("shrink-0", className) } as const;
  switch (health) {
    case "healthy":
      return (
        <svg {...props}>
          <circle cx="5" cy="5" r="3.5" fill="var(--fg-2)" />
        </svg>
      );
    case "degraded":
      return (
        <svg {...props}>
          <circle cx="5" cy="5" r="3.8" fill="var(--warn)" />
        </svg>
      );
    case "failing":
      return (
        <svg {...props}>
          <path d="M5 0.6 L9.6 9 H0.4 Z" fill="var(--warn)" />
        </svg>
      );
    case "expected-broken":
      return (
        <svg {...props}>
          <circle cx="5" cy="5" r="3.5" fill="none" stroke="var(--fg-2)" strokeWidth="1.3" />
          <path d="M5 1.5 A3.5 3.5 0 0 0 5 8.5 Z" fill="var(--fg-2)" />
        </svg>
      );
    case "leftover":
      return (
        <svg {...props}>
          <circle cx="5" cy="5" r="3.4" fill="none" stroke="var(--warn)" strokeWidth="1.5" />
        </svg>
      );
    case "stopped":
      return (
        <svg {...props}>
          <rect x="1.7" y="1.7" width="6.6" height="6.6" rx="1" fill="none" stroke="var(--fg-3)" strokeWidth="1.4" />
        </svg>
      );
    case "unknown":
      return (
        <svg {...props}>
          <circle cx="5" cy="5" r="3.5" fill="none" stroke="var(--fg-3)" strokeWidth="1.4" strokeDasharray="1.8 1.5" />
        </svg>
      );
  }
}

export function HealthBadge({ health, short, className }: { health: Health; short?: boolean; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-[12px] whitespace-nowrap", HEALTH_TEXT[health], className)}>
      <HealthMark health={health} />
      {short ? HEALTH_SHORT[health] : HEALTH[health].word}
    </span>
  );
}

export function nodeIcon(node: Pick<TopoNode, "id" | "kind" | "tags">): LucideIcon {
  if (node.tags.includes("fixture")) return node.kind === "service" ? Route : node.kind === "endpoints" ? Waypoints : FlaskConical;
  const byId: Record<string, LucideIcon> = { rag: Layers, ollama: Bot, operator: AppWindow, worker: Terminal, openai: Cloud, pgvector: Database };
  if (byId[node.id]) return byId[node.id];
  const byKind: Record<TopoNode["kind"], LucideIcon> = {
    host: Server,
    gpu: Microchip,
    runtime: Container,
    container: Container,
    process: Terminal,
    external: Cloud,
    profile: Boxes,
    "k8s-node": Cpu,
    namespace: Folder,
    pod: Box,
    service: Route,
    endpoints: Waypoints,
  };
  return byKind[node.kind];
}

export function NodeIcon({ node, className }: { node: Pick<TopoNode, "id" | "kind" | "tags">; className?: string }) {
  const Icon = nodeIcon(node);
  return <Icon aria-hidden className={clsx("size-3.5 shrink-0", className)} strokeWidth={1.75} />;
}

/** Live traffic marker: the accent means "active now". */
export function LiveDot({ className }: { className?: string }) {
  return (
    <span className={clsx("relative inline-flex size-1.5 shrink-0", className)} aria-hidden>
      <span className="absolute inset-0 rounded-full bg-accent opacity-60 motion-safe:animate-ping" />
      <span className="relative size-1.5 rounded-full bg-accent" />
    </span>
  );
}

export const FILTERS = [
  { id: "all", label: "All", healths: [] as Health[] },
  { id: "attention", label: "Attention", healths: ["failing", "degraded"] as Health[] },
  { id: "explained", label: "Explained", healths: ["expected-broken", "leftover"] as Health[] },
  { id: "inactive", label: "Stopped or unknown", healths: ["stopped", "unknown"] as Health[] },
  { id: "healthy", label: "Healthy", healths: ["healthy"] as Health[] },
] as const;
export type FilterId = (typeof FILTERS)[number]["id"];

export function matchesFilter(node: TopoNode, filter: FilterId, query: string) {
  const def = FILTERS.find((f) => f.id === filter)!;
  if (def.healths.length && !def.healths.includes(node.health)) return false;
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [node.name, node.ident, node.kindLabel, node.status, HEALTH[node.health].word].some((field) => field?.toLowerCase().includes(q));
}

export function FilterBar({
  graph,
  filter,
  onFilter,
  query,
  onQuery,
  className,
}: {
  graph: TopologyGraph;
  filter: FilterId;
  onFilter: (filter: FilterId) => void;
  query: string;
  onQuery: (query: string) => void;
  className?: string;
}) {
  const count = (id: FilterId) => graph.nodes.filter((n) => matchesFilter(n, id, "")).length;
  return (
    <div className={clsx("flex flex-wrap items-center gap-2", className)}>
      <label className="flex h-8 min-w-0 flex-1 items-center gap-2 rounded-md border border-line bg-surface px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent sm:max-w-64">
        <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
        <input value={query} onChange={(e) => onQuery(e.target.value)} placeholder="Search components" aria-label="Search components" className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
        {query && (
          <button type="button" onClick={() => onQuery("")} aria-label="Clear search" className="cursor-pointer rounded text-fg-3 hover:text-fg">
            <X className="size-3.5" strokeWidth={2} />
          </button>
        )}
      </label>
      <div className="-mx-1 flex max-w-full items-center gap-1 overflow-x-auto px-1" role="group" aria-label="Filter by health">
        {FILTERS.map((f) => {
          const n = count(f.id);
          return (
            <button
              key={f.id}
              type="button"
              aria-pressed={filter === f.id}
              onClick={() => onFilter(f.id)}
              disabled={f.id !== "all" && n === 0}
              className={clsx(
                "inline-flex h-7 shrink-0 cursor-pointer items-center gap-1.5 rounded-md border px-2 text-[12px] transition-colors disabled:cursor-default disabled:opacity-40",
                filter === f.id ? "border-line-strong bg-surface-3 text-fg" : "border-line text-fg-3 hover:text-fg",
              )}
            >
              {f.id !== "all" && <HealthMark health={f.healths[0]} size={9} />}
              {f.label}
              <span className="num text-[11px] text-fg-3">{n}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** "Knowledge · KubeLLM worker → RAG API → pgvector" for the current phase. */
export function TrafficLine({ graph, className, compact }: { graph: TopologyGraph; className?: string; compact?: boolean }) {
  const paths = graph.traffic.paths.filter((p) => !(p[0] === "operator" && p.length === 2));
  return (
    <div className={clsx("flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px]", className)}>
      <span className="inline-flex items-center gap-1.5 text-fg-2">
        {graph.campaignStatus === "running" && graph.phase ? <LiveDot /> : <span className="size-1.5 rounded-full border border-fg-3" aria-hidden />}
        <span className="font-medium text-fg">{graph.traffic.label}</span>
        {graph.attempt && graph.phase && !compact && <span className="num text-fg-3">· attempt {graph.attempt.index + 1}</span>}
      </span>
      {paths.map((path) => (
        <span key={path.join(">")} className="inline-flex min-w-0 items-center gap-1 text-fg-3">
          {path.map((id, i) => (
            <span key={id} className="inline-flex items-center gap-1">
              {i > 0 && <ArrowRight className="size-3 shrink-0 text-accent" strokeWidth={2} aria-label="calls" />}
              <span className="truncate text-fg-2">{graph.byId.get(id)?.name ?? id}</span>
            </span>
          ))}
        </span>
      ))}
    </div>
  );
}

export function DemoTag() {
  return (
    <Tip content="Simulated lab state shaped by the Nov 1, 2026 survey and driven by the demo replay. Nothing here reads the lab.">
      <span>
        <Tag tone="accent">Demo</Tag>
      </span>
    </Tip>
  );
}

/** Lane health: the lane's profile, services, and worker. Explained items are named, not counted. */
export function LaneHealth({ graph, className }: { graph: TopologyGraph; className?: string }) {
  const lane = graph.lane;
  return (
    <Tip content={lane.reason}>
      <span tabIndex={0} className={clsx("inline-flex items-center gap-2 text-[12.5px]", className)}>
        <span className="text-fg-3">Lane minh</span>
        <HealthBadge health={lane.health} />
        {lane.explained.length > 0 && <span className="text-fg-3">· {lane.explained.length} explained</span>}
      </span>
    </Tip>
  );
}

const EFFECT_STYLE: Record<Effect, string> = {
  down: "border-warn/45 bg-warn-soft text-warn",
  impaired: "border-warn/30 text-warn",
  outcome: "border-line-strong text-fg-2",
};

export function EffectChip({ effect }: { effect: Effect }) {
  return <span className={clsx("inline-flex h-5 shrink-0 items-center rounded-[4px] border px-1.5 text-[11px] font-medium whitespace-nowrap", EFFECT_STYLE[effect])}>{EFFECT[effect].word}</span>;
}

function LinkRow({ graph, link, direction, onSelect }: { graph: TopologyGraph; link: Link; direction: "up" | "down"; onSelect: (id: string) => void }) {
  const node = graph.byId.get(link.id);
  if (!node) return null;
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(node.id)}
        className="grid w-full cursor-pointer grid-cols-[10px_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12.5px] hover:bg-surface-2"
      >
        <HealthMark health={node.health} />
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="truncate text-fg">{node.name}</span>
          {link.edge.active && <LiveDot />}
        </span>
        <Tip content={`${EDGE_KIND[link.edge.kind].word}: ${direction === "up" ? "this node → " + node.name : node.name + " → this node"}. ${link.edge.impact}`}>
          <span className="font-mono text-[11px] text-fg-3">{link.edge.label}</span>
        </Tip>
      </button>
    </li>
  );
}

function Section({ title, count, children, aside }: { title: string; count?: number; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="grid gap-1.5 border-t border-line pt-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="label !text-[10px]">
          {title}
          {count !== undefined && <span className="ml-1.5 text-fg-3">{count}</span>}
        </h4>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function WhatIfPanel({ graph, impact, onSelect }: { graph: TopologyGraph; impact: WhatIf; onSelect: (id: string) => void }) {
  const counts = { down: 0, impaired: 0, outcome: 0 };
  for (const i of impact.impacts) counts[i.effect] += 1;
  return (
    <div className="grid gap-2.5 rounded-md border border-warn/30 bg-warn-soft/40 p-3">
      <div className="flex items-start gap-2 text-[12.5px]">
        <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-warn" strokeWidth={2} />
        <div className="min-w-0">
          <div className="font-medium text-fg">
            {impact.impacts.length ? `${impact.impacts.length} affected` : "Nothing else affected"}
            {impact.impacts.length > 0 && (
              <span className="font-normal text-fg-2">
                {" "}
                · {[counts.down && `${counts.down} go down`, counts.impaired && `${counts.impaired} impaired`, counts.outcome && `${counts.outcome} attempt outcome`].filter(Boolean).join(", ")}
              </span>
            )}
          </div>
          <div className="text-fg-3">Simulated. Nothing is stopped.</div>
        </div>
      </div>
      {impact.impacts.length > 0 && (
        <ol className="grid gap-1">
          {impact.impacts.map((item) => {
            const node = graph.byId.get(item.id)!;
            const via = graph.byId.get(item.via);
            return (
              <li key={item.id}>
                <button type="button" onClick={() => onSelect(item.id)} className="grid w-full cursor-pointer gap-0.5 rounded-md px-2 py-1.5 text-left hover:bg-surface-2/70">
                  <span className="flex min-w-0 items-center gap-2 text-[12.5px]">
                    <span className="num w-4 shrink-0 text-[11px] text-fg-3">{item.depth}</span>
                    <span className="truncate text-fg">{node.name}</span>
                    <span className="ml-auto">
                      <EffectChip effect={item.effect} />
                    </span>
                  </span>
                  <span className="pl-6 text-[12px] leading-snug text-fg-2">{item.reason}</span>
                  {item.depth > 1 && via && <span className="pl-6 text-[11.5px] text-fg-3">via {via.name}</span>}
                </button>
              </li>
            );
          })}
        </ol>
      )}
      {impact.blocked.length > 0 && (
        <div className="grid gap-1.5 border-t border-warn/20 pt-2">
          <div className="text-[12px] text-fg-2">Preflight would block new campaigns:</div>
          <div className="flex flex-wrap gap-1">
            {impact.blocked.map((check) => (
              <Tip key={check.id} content={check.detail}>
                <span tabIndex={0} className="inline-flex h-5 items-center rounded-[4px] border border-line-strong px-1.5 font-mono text-[10.5px] text-fg-2">
                  {check.label}
                </span>
              </Tip>
            ))}
          </div>
        </div>
      )}
      {impact.notes.map((note) => (
        <p key={note} className="text-[12px] leading-snug text-fg-3">
          {note}
        </p>
      ))}
    </div>
  );
}

export function WhatIfToggle({ on, onChange, className }: { on: boolean; onChange: (on: boolean) => void; className?: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={() => onChange(!on)}
      className={clsx(
        "inline-flex h-8 cursor-pointer items-center justify-center gap-1.5 rounded-md border px-3 text-[12.5px] font-medium transition-colors",
        on ? "border-warn/50 bg-warn-soft text-warn" : "border-line-strong text-fg hover:bg-surface-2",
        className,
      )}
    >
      <TriangleAlert className="size-3.5" strokeWidth={2} />
      {on ? "Showing what fails" : "What if this fails?"}
    </button>
  );
}

export function ChangeList({ id, limit = 5 }: { id: string; limit?: number }) {
  const { campaign, t } = useReplay();
  const changes = useMemo(() => (campaign ? changesFor(campaign, id, Math.floor(t), limit) : []), [campaign, id, t, limit]);
  if (!changes.length) return <p className="text-[12px] text-fg-3">No changes yet in this replay.</p>;
  return (
    <ol className="grid gap-1">
      {changes.map((change, i) => (
        <li key={`${change.t}-${i}`} className="grid grid-cols-[44px_10px_minmax(0,1fr)] items-start gap-2 text-[12px]">
          <span className="num pt-px text-fg-3">{clock(change.t)}</span>
          <HealthMark health={change.to.health} className="mt-[3px]" />
          <span className="min-w-0">
            <span className={clsx("block truncate", i === 0 ? "text-fg" : "text-fg-2")}>{change.to.status}</span>
            <span className="block truncate text-[11.5px] text-fg-3">
              {change.from ? `${HEALTH[change.to.health].word}` : "First seen"}
              {change.attempt !== undefined ? ` · attempt ${change.attempt + 1}${change.phase ? `, ${change.phase.toLowerCase()}` : ""}` : ""}
              {change.from && change.from.name !== change.to.name ? ` · ${change.to.name}` : ""}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}

/**
 * The node inspector every option shares: health and why, what it contains,
 * what it needs, what needs it, the simulated failure, facts, and how it
 * changed during the replay.
 */
export function Inspector({
  graph,
  id,
  onSelect,
  whatIfOn,
  onWhatIf,
  impact,
  header,
  footer,
  className,
  hideWhatIf,
}: {
  graph: TopologyGraph;
  id: string;
  onSelect: (id: string) => void;
  whatIfOn: boolean;
  onWhatIf: (on: boolean) => void;
  impact?: WhatIf;
  header?: ReactNode;
  footer?: ReactNode;
  className?: string;
  /** The option shows the simulated failure elsewhere. */
  hideWhatIf?: boolean;
}) {
  const node = graph.byId.get(id);
  if (!node) {
    return (
      <div className={clsx("grid content-start gap-2 p-4 text-[12.5px] text-fg-3", className)}>
        <p>That component isn't present at this moment of the replay.</p>
      </div>
    );
  }
  const rollup = graph.rollups.get(id);
  const ups = upstream(graph, id);
  const downs = downstream(graph, id);
  const parent = node.parent ? graph.byId.get(node.parent) : undefined;
  return (
    <div className={clsx("grid content-start gap-3 p-4", className)}>
      {header}
      <div className="grid gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="label !text-[10px]">{node.kindLabel}</span>
          {node.tags.includes("selected-lane") && <Tag tone="accent">Selected lane</Tag>}
          {node.tags.includes("default-context") && <Tag>Default context</Tag>}
          {node.tags.includes("read-only") && <Tag>Read-only</Tag>}
          {node.scope === "shared" && <Tag>Shared</Tag>}
          {node.scope === "other" && !node.tags.includes("read-only") && <Tag>Other account</Tag>}
        </div>
        <div className="flex items-start gap-2">
          <NodeIcon node={node} className="mt-[3px] text-fg-3" />
          <h3 className="min-w-0 font-mono text-[14.5px] leading-snug font-medium break-all">{node.name}</h3>
        </div>
        {(node.ident || parent) && (
          <div className="flex flex-wrap gap-x-2 text-[12px] text-fg-3">
            {node.ident && <span className="font-mono">{node.ident}</span>}
            {parent && (
              <button type="button" onClick={() => onSelect(parent.id)} className="cursor-pointer hover:text-fg">
                in {parent.name}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid gap-1.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <HealthBadge health={node.health} className="text-[12.5px]" />
          <span className="text-[12.5px] text-fg-3">·</span>
          <span className="flex min-w-0 items-center gap-1.5 text-[12.5px] text-fg-2">
            {node.active && <LiveDot />}
            {node.status}
          </span>
        </div>
        <p className="text-[12.5px] leading-relaxed text-fg-2">{node.reason}</p>
        {rollup && rollup.total > 0 && (
          <div className="grid gap-1 rounded-md bg-surface-2 px-2.5 py-2 text-[12px]">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-fg-3">Contents</span>
              <HealthBadge health={rollup.attention.length ? (rollup.counts.failing ? "failing" : "degraded") : "healthy"} />
              {(Object.keys(rollup.counts) as Health[])
                .filter((h) => rollup.counts[h])
                .map((h) => (
                  <span key={h} className="inline-flex items-center gap-1 text-fg-3" title={HEALTH[h].word}>
                    <HealthMark health={h} size={9} />
                    <span className="num">{rollup.counts[h]}</span>
                    <span className="sr-only">{HEALTH[h].word}</span>
                  </span>
                ))}
            </div>
            <p className="leading-snug text-fg-2">{rollup.reason}</p>
          </div>
        )}
      </div>

      {!hideWhatIf && <WhatIfToggle on={whatIfOn} onChange={onWhatIf} className="w-full" />}
      {!hideWhatIf && whatIfOn && impact && <WhatIfPanel graph={graph} impact={impact} onSelect={onSelect} />}

      <Section title="Depends on" count={ups.length}>
        {ups.length ? (
          <ul className="-mx-2 grid">
            {ups.map((link) => (
              <LinkRow key={link.edge.id} graph={graph} link={link} direction="up" onSelect={onSelect} />
            ))}
          </ul>
        ) : (
          <p className="text-[12px] text-fg-3">Nothing: it's a foundation.</p>
        )}
      </Section>
      <Section title="Needed by" count={downs.length}>
        {downs.length ? (
          <ul className="-mx-2 grid">
            {downs.map((link) => (
              <LinkRow key={link.edge.id} graph={graph} link={link} direction="down" onSelect={onSelect} />
            ))}
          </ul>
        ) : (
          <p className="text-[12px] text-fg-3">Nothing depends on it.</p>
        )}
      </Section>

      {node.facts.length > 0 && (
        <Section title="Facts">
          <dl className="grid gap-1 text-[12px]">
            {node.facts.map((fact) => (
              <div key={fact.label} className="grid grid-cols-[96px_minmax(0,1fr)] gap-2">
                <dt className="text-fg-3">{fact.label}</dt>
                <dd className="break-words text-fg">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </Section>
      )}
      <Section title="Recent changes">
        <ChangeList id={id} />
      </Section>
      {footer}
    </div>
  );
}
