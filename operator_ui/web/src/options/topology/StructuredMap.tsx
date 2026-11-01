import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import { Fragment, useCallback, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Tag } from "@/components/ui";
import { downstreamAll, upstreamAll, whatIf, type TopologyGraph, type WhatIf } from "@/demo/topologyGraph";
import { StageFallback } from "../OptionsRoom";
import { DemoTag, EffectChip, FilterBar, HEALTH_SHORT, HEALTH_TEXT, HealthMark, Inspector, LaneHealth, LiveDot, matchesFilter, NodeIcon, TrafficLine, useGraph, type FilterId } from "./shared";

// A containment tree in two columns (the lab host, then the selected lane's
// cluster) with a persistent inspector. Selecting any row marks what it needs
// and what needs it across both columns; the what-if toggle replaces those
// marks with the simulated blast radius.

interface Row {
  key: string;
  id: string;
  depth: number;
  collapsible?: boolean;
  /** A pointer to a node shown in full elsewhere. */
  alias?: string;
}

const SYSTEM = ["sys:kube-apiserver", "sys:etcd", "sys:kube-controller-manager", "sys:kube-scheduler", "sys:kube-proxy", "sys:coredns", "sys:storage-provisioner"];

function columns(graph: TopologyGraph, collapsed: Set<string>): { id: string; title: string; caption: string; rows: Row[] }[] {
  const row = (id: string, depth: number, extra: Partial<Row> = {}): Row[] => (graph.byId.has(id) ? [{ key: extra.alias ? `${id}@alias` : id, id, depth, ...extra }] : []);
  const kids = (id: string, depth: number, ids: string[]) => (collapsed.has(id) ? [] : ids.flatMap((child) => row(child, depth)));
  const fixture = ["fixture:pod", "fixture:svc", "fixture:ep"];
  return [
    {
      id: "host",
      title: "Lab host",
      caption: "Processes, devices, and containers on the lab server",
      rows: [
        ...row("host", 0),
        ...["operator", "worker", "rag", "ollama", "gpu-0", "gpu-1"].flatMap((id) => row(id, 1)),
        ...row("docker", 1, { collapsible: true }),
        ...(collapsed.has("docker")
          ? []
          : [
              ...row("pgvector", 2),
              ...row("profile:minh-lane", 2, { alias: "Expanded in the lane column" }),
              ...["profile:minikube", "profile:minh", "profile:lamap", "profile:xyz"].flatMap((id) => row(id, 2)),
            ]),
        ...row("openai", 0),
      ],
    },
    {
      id: "lane",
      title: "Lane minh-lane",
      caption: "Read through the lane's own kubeconfig",
      rows: [
        ...row("profile:minh-lane", 0),
        ...row("node:minh-lane", 1),
        ...row("ns:default", 1, { collapsible: true }),
        ...kids("ns:default", 2, [...fixture, "pod:curl-pod", "pod:tmpcurl"]),
        ...row("ns:kube-system", 1, { collapsible: true }),
        ...kids("ns:kube-system", 2, SYSTEM),
      ],
    },
  ];
}

type Relation = { kind: "up" | "down"; depth: number } | undefined;

function RelationChip({ relation }: { relation: Relation }) {
  if (!relation) return null;
  const word = relation.kind === "up" ? "Dependency" : "Dependent";
  return (
    <span
      className={clsx(
        "inline-flex h-5 shrink-0 items-center gap-1 rounded-[4px] border px-1.5 text-[11px] whitespace-nowrap",
        relation.depth === 1 ? "border-line-strong text-fg-2" : "border-line text-fg-3",
      )}
    >
      {word}
      {relation.depth > 1 && <span className="num">· {relation.depth} hops</span>}
    </span>
  );
}

function MapRow({
  graph,
  row,
  selected,
  relation,
  impact,
  dim,
  focused,
  collapsed,
  onSelect,
  onToggle,
  onKeyDown,
}: {
  graph: TopologyGraph;
  row: Row;
  selected: boolean;
  relation: Relation;
  impact?: WhatIf;
  dim: boolean;
  focused: boolean;
  collapsed: boolean;
  onSelect: () => void;
  onToggle?: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}) {
  const node = graph.byId.get(row.id)!;
  const rollup = graph.rollups.get(row.id);
  const shownHealth = rollup && !row.alias ? rollup.health : node.health;
  const hit = impact?.byId.get(row.id);
  const root = impact?.root === row.id;
  const explained = rollup?.explained.length ?? 0;
  return (
    <div
      className={clsx(
        "relative flex items-stretch transition-opacity duration-200",
        selected && "bg-accent-soft",
        dim && "opacity-40",
        root && "bg-warn-soft",
        hit?.effect === "down" && "bg-warn-soft/60",
      )}
    >
      {selected && <span className="absolute inset-y-0 left-0 w-0.5 bg-accent" aria-hidden />}
      <span style={{ width: 12 + row.depth * 18 }} className="shrink-0" aria-hidden />
      {row.collapsible ? (
        <button type="button" tabIndex={-1} onClick={onToggle} aria-label={`${collapsed ? "Expand" : "Collapse"} ${node.name}`} aria-expanded={!collapsed} className="-ml-1 grid w-5 shrink-0 cursor-pointer place-items-center text-fg-3 hover:text-fg">
          <ChevronRight className={clsx("size-3.5 transition-transform", !collapsed && "rotate-90")} strokeWidth={2} />
        </button>
      ) : (
        <span className="w-4 shrink-0" aria-hidden />
      )}
      <button
        type="button"
        data-row={row.key}
        tabIndex={focused ? 0 : -1}
        aria-pressed={selected}
        aria-label={`${node.name}, ${node.kindLabel}, ${HEALTH_SHORT[shownHealth]}, ${node.status}`}
        onClick={onSelect}
        onKeyDown={onKeyDown}
        className="grid min-w-0 flex-1 cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 py-2 pr-3 text-left outline-none focus-visible:bg-surface-2"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <NodeIcon node={node} className={selected ? "text-accent" : "text-fg-3"} />
          <span className={clsx("truncate text-[13px]", row.depth === 0 ? "font-medium" : "", node.kind === "pod" || node.kind === "service" || node.kind === "endpoints" ? "font-mono text-[12.5px]" : "", row.alias ? "text-fg-2" : "text-fg")}>{node.name}</span>
          {node.active && <LiveDot />}
          {node.tags.includes("selected-lane") && !row.alias && <Tag tone="accent">Selected</Tag>}
          {node.tags.includes("default-context") && <Tag>Default context</Tag>}
        </span>
        <span className={clsx("inline-flex items-center gap-1.5 justify-self-end text-[12px] whitespace-nowrap", HEALTH_TEXT[shownHealth])}>
          <HealthMark health={shownHealth} />
          {HEALTH_SHORT[shownHealth]}
        </span>
        <span className="flex min-w-0 items-center gap-1.5 pl-5 text-[12px] text-fg-3">
          <span className="truncate">{row.alias ?? node.status}</span>
          {!row.alias && rollup && explained > 0 && <span className="shrink-0">· {explained} explained</span>}
          {!row.alias && node.ident && node.kind !== "pod" && <span className="hidden truncate font-mono text-[11.5px] sm:inline">· {node.ident}</span>}
        </span>
        <span className="flex justify-end">{root ? <Tag tone="warn">Simulated failure</Tag> : hit ? <EffectChip effect={hit.effect} /> : <RelationChip relation={relation} />}</span>
      </button>
    </div>
  );
}

export default function StructuredMap() {
  const { graph } = useGraph();
  const [selected, setSelected] = useState("profile:minh-lane");
  const [whatIfOn, setWhatIfOn] = useState(false);
  const [filter, setFilter] = useState<FilterId>("all");
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set(["ns:kube-system"]));
  const [focusKey, setFocusKey] = useState<string>("profile:minh-lane");
  const root = useRef<HTMLDivElement>(null);

  const impact = useMemo(() => (graph && whatIfOn ? whatIf(graph, selected) : undefined), [graph, whatIfOn, selected]);
  const relations = useMemo(() => {
    if (!graph) return new Map<string, Relation>();
    const map = new Map<string, Relation>();
    for (const [id, depth] of downstreamAll(graph, selected, 3)) map.set(id, { kind: "down", depth });
    for (const [id, depth] of upstreamAll(graph, selected, 3)) map.set(id, { kind: "up", depth });
    return map;
  }, [graph, selected]);

  const toggle = useCallback((id: string) => {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // A searched or filtered row keeps its ancestors visible for context.
  const visible = useMemo(() => {
    if (!graph) return undefined;
    if (filter === "all" && !query.trim()) return undefined;
    const keep = new Set<string>();
    for (const node of graph.nodes) {
      if (!matchesFilter(node, filter, query)) continue;
      keep.add(node.id);
      let parent = node.parent;
      while (parent) {
        keep.add(parent);
        parent = graph.byId.get(parent)?.parent;
      }
    }
    return keep;
  }, [graph, filter, query]);

  const cols = useMemo(() => (graph ? columns(graph, visible ? new Set() : collapsed) : []), [graph, collapsed, visible]);
  const flat = cols.flatMap((c) => c.rows.filter((r) => !visible || visible.has(r.id)));

  if (!graph) return <StageFallback />;

  const select = (id: string, key?: string) => {
    setSelected(id);
    setFocusKey(key ?? id);
  };

  const onRowKey = (event: KeyboardEvent<HTMLButtonElement>, index: number, row: Row) => {
    const move = (to: number) => {
      const next = flat[Math.max(0, Math.min(flat.length - 1, to))];
      if (!next) return;
      select(next.id, next.key);
      root.current?.querySelector<HTMLElement>(`[data-row="${CSS.escape(next.key)}"]`)?.focus();
    };
    if (event.key === "ArrowDown") {
      event.preventDefault();
      move(index + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      move(index - 1);
    } else if (event.key === "ArrowRight" && row.collapsible && collapsed.has(row.id)) {
      event.preventDefault();
      toggle(row.id);
    } else if (event.key === "ArrowLeft" && row.collapsible && !collapsed.has(row.id)) {
      event.preventDefault();
      toggle(row.id);
    } else if (event.key === "w") {
      setWhatIfOn((on) => !on);
    } else if (event.key === "Escape") {
      setWhatIfOn(false);
    }
  };

  const inspector = (className?: string) => (
    <Inspector graph={graph} id={selected} onSelect={(id) => select(id)} whatIfOn={whatIfOn} onWhatIf={setWhatIfOn} impact={impact} className={className} />
  );

  return (
    <div className="grid gap-3" ref={root}>
      <div className="grid gap-2 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <DemoTag />
          <LaneHealth graph={graph} />
          <span className="text-[12.5px] text-fg-3">
            Default kubectl context <span className="font-mono text-fg-2">minikube</span> · never used to pick a target
          </span>
        </div>
        <TrafficLine graph={graph} />
      </div>
      <FilterBar graph={graph} filter={filter} onFilter={setFilter} query={query} onQuery={setQuery} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="grid content-start gap-4 lg:grid-cols-2">
          {cols.map((col) => {
            const rows = col.rows.filter((r) => !visible || visible.has(r.id));
            return (
              <section key={col.id} className={clsx("min-w-0 self-start overflow-hidden rounded-lg border bg-surface", col.id === "lane" ? "border-accent-line" : "border-line")}>
                <header className="border-b border-line px-4 py-2.5">
                  <h3 className="text-[13px] font-medium">{col.title}</h3>
                  <p className="text-[12px] text-fg-3">{col.caption}</p>
                </header>
                {rows.length ? (
                  <ul className="divide-y divide-line">
                    {rows.map((row) => {
                      const index = flat.findIndex((r) => r.key === row.key);
                      const isSelected = row.id === selected;
                      const dim = impact ? !impact.byId.has(row.id) && impact.root !== row.id : !!visible && !matchesFilter(graph.byId.get(row.id)!, filter, query);
                      return (
                        <Fragment key={row.key}>
                          <li>
                            <MapRow
                              graph={graph}
                              row={row}
                              selected={isSelected}
                              relation={relations.get(row.id)}
                              impact={impact}
                              dim={dim}
                              focused={focusKey === row.key || (!flat.some((r) => r.key === focusKey) && index === 0)}
                              collapsed={collapsed.has(row.id)}
                              onSelect={() => select(row.id, row.key)}
                              onToggle={row.collapsible ? () => toggle(row.id) : undefined}
                              onKeyDown={(event) => onRowKey(event, index, row)}
                            />
                          </li>
                          {isSelected && focusKey === row.key && <li className="border-t border-accent-line bg-bg/40 xl:hidden">{inspector()}</li>}
                        </Fragment>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="px-4 py-6 text-center text-[12.5px] text-fg-3">Nothing here matches.</p>
                )}
              </section>
            );
          })}
        </div>
        <aside className="hidden min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface xl:sticky xl:top-20 xl:block xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto">
          {inspector()}
        </aside>
      </div>
      <p className="text-[12px] leading-relaxed text-fg-3">
        Demo state shaped by the lab survey (Nov 1, 2026). Containers summarize their contents; fixtures broken by design and known leftovers are listed as explained and never count against the lane. Arrow keys move between rows, W shows what fails.
      </p>
    </div>
  );
}
