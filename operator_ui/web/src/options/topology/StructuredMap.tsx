import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import { Tag } from "@/components/ui";
import { downstreamAll, upstreamAll, type TopologyGraph, type WhatIf } from "@/demo/topologyGraph";
import { EffectChip, FilterBar, HEALTH_SHORT, HEALTH_TEXT, HealthMark, LiveDot, matchesFilter, NodeIcon, type FilterId } from "./shared";

interface Row {
  key: string;
  id: string;
  depth: number;
  collapsible?: boolean;
  /** Inside the selected lane's cluster, read through the lane's own kubeconfig. */
  lane?: boolean;
}

const SYSTEM = ["sys:kube-apiserver", "sys:etcd", "sys:kube-controller-manager", "sys:kube-scheduler", "sys:kube-proxy", "sys:coredns", "sys:storage-provisioner"];

/** One containment tree: the lab server, its processes and containers, and the selected lane's cluster nested inside its minikube profile. */
function tree(graph: TopologyGraph, collapsed: Set<string>): Row[] {
  const row = (id: string, depth: number, extra: Partial<Row> = {}): Row[] => (graph.byId.has(id) ? [{ key: id, id, depth, ...extra }] : []);
  const kids = (id: string, depth: number, ids: string[]) => (collapsed.has(id) ? [] : ids.flatMap((child) => row(child, depth, { lane: true })));
  const fixture = ["fixture:pod", "fixture:svc", "fixture:ep"];
  return [
    ...row("host", 0),
    ...["operator", "worker", "rag", "ollama", "gpu-0", "gpu-1"].flatMap((id) => row(id, 1)),
    ...row("docker", 1, { collapsible: true }),
    ...(collapsed.has("docker")
      ? []
      : [
          ...row("pgvector", 2),
          ...row("profile:minh-lane", 2, { collapsible: true }),
          ...(collapsed.has("profile:minh-lane")
            ? []
            : [
                ...row("node:minh-lane", 3, { lane: true }),
                ...row("ns:default", 3, { collapsible: true, lane: true }),
                ...kids("ns:default", 4, [...fixture, "pod:curl-pod", "pod:tmpcurl"]),
                ...row("ns:kube-system", 3, { collapsible: true, lane: true }),
                ...kids("ns:kube-system", 4, SYSTEM),
              ]),
          ...["profile:minikube", "profile:minh", "profile:lamap", "profile:xyz"].flatMap((id) => row(id, 2)),
        ]),
    ...row("openai", 0),
  ];
}

// Indentation per depth, narrower on phones so deep rows keep their names.
const indent = (depth: number) => ({ "--depth": depth }) as CSSProperties;

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
  const shownHealth = rollup ? rollup.health : node.health;
  const hit = impact?.byId.get(row.id);
  const root = impact?.root === row.id;
  const explained = rollup?.explained.length ?? 0;
  return (
    <div
      style={indent(row.depth)}
      className={clsx(
        "relative flex items-stretch transition-opacity duration-200",
        selected && "bg-accent-soft",
        dim && "opacity-40",
        root && "bg-warn-soft",
        hit?.effect === "down" && "bg-warn-soft/60",
      )}
    >
      {selected && <span className="absolute inset-y-0 left-0 w-0.5 bg-accent" aria-hidden />}
      {row.lane && <span className="absolute inset-y-0 left-[42px] w-px bg-accent-line sm:left-[54px]" aria-hidden />}
      <span className="w-[calc(12px_+_var(--depth)_*_12px)] shrink-0 sm:w-[calc(12px_+_var(--depth)_*_18px)]" aria-hidden />
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
          <span className={clsx("truncate text-[13px] text-fg", row.depth === 0 ? "font-medium" : "", node.kind === "pod" || node.kind === "service" || node.kind === "endpoints" ? "font-mono text-[12.5px]" : "")}>{node.name}</span>
          {node.active && <LiveDot />}
          {node.tags.includes("selected-lane") && <Tag tone="accent">Selected lane</Tag>}
          {node.tags.includes("default-context") && <Tag>Default context</Tag>}
        </span>
        <span className={clsx("inline-flex items-center gap-1.5 justify-self-end text-[12px] whitespace-nowrap", HEALTH_TEXT[shownHealth])}>
          <HealthMark health={shownHealth} />
          {HEALTH_SHORT[shownHealth]}
        </span>
        <span className="flex min-w-0 items-center gap-1.5 pl-5 text-[12px] text-fg-3">
          <span className="truncate">{node.status}</span>
          {rollup && explained > 0 && <span className="shrink-0">· {explained} explained</span>}
          {node.ident && node.kind !== "pod" && <span className="hidden truncate font-mono text-[11.5px] sm:inline">· {node.ident}</span>}
        </span>
        <span className="flex justify-end">{root ? <Tag tone="warn">Simulated failure</Tag> : hit ? <EffectChip effect={hit.effect} /> : <RelationChip relation={relation} />}</span>
      </button>
    </div>
  );
}

/**
 * The containment tree: the lab server, then the selected lane's cluster inside its profile.
 * Selecting a row marks what it needs and what needs it across the tree;
 * with the simulated failure on, those marks become what goes down. The
 * explorer owns the selection and the explanation panel, which sits beside
 * the map on wide screens and opens under the selected row on narrow ones.
 */
export function MapView({
  graph,
  selected,
  onSelect,
  impact,
  onToggleWhatIf,
  onWhatIfOff,
  panel,
}: {
  graph: TopologyGraph;
  selected: string;
  onSelect: (id: string) => void;
  impact?: WhatIf;
  onToggleWhatIf: () => void;
  onWhatIfOff: () => void;
  panel: ReactNode;
}) {
  const [filter, setFilter] = useState<FilterId>("all");
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set(["ns:kube-system"]));
  const root = useRef<HTMLDivElement>(null);

  const relations = useMemo(() => {
    const map = new Map<string, Relation>();
    for (const [id, depth] of downstreamAll(graph, selected, 3)) map.set(id, { kind: "down", depth });
    for (const [id, depth] of upstreamAll(graph, selected, 3)) map.set(id, { kind: "up", depth });
    return map;
  }, [graph, selected]);

  // A selection made elsewhere (the panel, the timeline) opens the branches
  // that hide it and brings its row into view; the first render never scrolls.
  const mounted = useRef(false);
  useEffect(() => {
    const hidden = [...collapsed].filter((id) => {
      let parent = graph.byId.get(selected)?.parent;
      while (parent) {
        if (parent === id) return true;
        parent = graph.byId.get(parent)?.parent;
      }
      return false;
    });
    if (hidden.length) setCollapsed((current) => new Set([...current].filter((id) => !hidden.includes(id))));
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    requestAnimationFrame(() => {
      const row = root.current?.querySelector<HTMLElement>(`[data-row="${CSS.escape(selected)}"]`);
      if (row && row !== document.activeElement) row.scrollIntoView({ block: "nearest" });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when the selection changes
  }, [selected]);

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

  const rows = useMemo(() => tree(graph, visible ? new Set() : collapsed).filter((r) => !visible || visible.has(r.id)), [graph, collapsed, visible]);
  const selectedShown = rows.some((r) => r.id === selected);

  const onRowKey = (event: KeyboardEvent<HTMLButtonElement>, index: number, row: Row) => {
    const move = (to: number) => {
      const next = rows[Math.max(0, Math.min(rows.length - 1, to))];
      if (!next) return;
      onSelect(next.id);
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
      onToggleWhatIf();
    } else if (event.key === "Escape") {
      onWhatIfOff();
    }
  };

  return (
    <div className="grid content-start gap-3" ref={root}>
      <FilterBar graph={graph} filter={filter} onFilter={setFilter} query={query} onQuery={setQuery} />
      <section className="min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface">
        <header className="border-b border-line px-4 py-2.5">
          <h3 className="text-[13px] font-medium">Lab server and lane</h3>
          <p className="text-[12px] text-fg-3">Processes, devices, and containers on the lab server, with the selected lane's cluster inside its minikube profile</p>
        </header>
        {rows.length ? (
          <ul className="divide-y divide-line">
            {rows.map((row, index) => {
              const isSelected = row.id === selected;
              const dim = impact ? !impact.byId.has(row.id) && impact.root !== row.id : !!visible && !matchesFilter(graph.byId.get(row.id)!, filter, query);
              const laneStarts = row.lane && !rows[index - 1]?.lane;
              return (
                <Fragment key={row.key}>
                  {laneStarts && (
                    <li style={indent(row.depth)} className="relative flex items-center bg-accent-soft/40 py-1.5 pr-3">
                      <span className="absolute inset-y-0 left-[42px] w-px bg-accent-line sm:left-[54px]" aria-hidden />
                      <span className="w-[calc(12px_+_var(--depth)_*_12px_+_16px)] shrink-0 sm:w-[calc(12px_+_var(--depth)_*_18px_+_16px)]" aria-hidden />
                      <span className="min-w-0 truncate text-[11.5px] text-fg-3">
                        Inside the lane · read through <span className="font-mono text-fg-2">minh-lane</span>'s own kubeconfig
                      </span>
                    </li>
                  )}
                  <li>
                    <MapRow
                      graph={graph}
                      row={row}
                      selected={isSelected}
                      relation={relations.get(row.id)}
                      impact={impact}
                      dim={dim}
                      focused={isSelected || (!selectedShown && index === 0)}
                      collapsed={collapsed.has(row.id)}
                      onSelect={() => onSelect(row.id)}
                      onToggle={row.collapsible ? () => toggle(row.id) : undefined}
                      onKeyDown={(event) => onRowKey(event, index, row)}
                    />
                  </li>
                  {isSelected && <li className="border-t border-accent-line bg-bg/40 xl:hidden">{panel}</li>}
                </Fragment>
              );
            })}
          </ul>
        ) : (
          <p className="px-4 py-6 text-center text-[12.5px] text-fg-3">Nothing here matches.</p>
        )}
      </section>
    </div>
  );
}
