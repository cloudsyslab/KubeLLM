import clsx from "clsx";
import { ChevronRight, Clock, CornerDownLeft, Radio } from "lucide-react";
import { Fragment, memo, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import { displayModel } from "@/components/charts";
import { LabLogo } from "@/components/ModelCard";
import { Segmented } from "@/components/ui";
import { labOf } from "@/data/models";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { downstreamAll, graphAt, HEALTH, phaseColumns, upstreamAll, whatIf, type Health, type NodeState, type PhaseColumn } from "@/demo/topologyGraph";
import { humanize } from "@/lib/cases";
import { StageFallback } from "../OptionsRoom";
import { DemoTag, HEALTH_SHORT, HealthBadge, HealthMark, Inspector, LaneHealth, NodeIcon, useGraph, WhatIfPanel, WhatIfToggle } from "./shared";

// Components down the side, every phase of every attempt across the top: the
// matrix answers "what was affected, and when" for the whole replay so far.
// Cells are sampled at each phase's midpoint.

interface RowDef {
  id: string;
  group: string;
}

const GROUPS: { label: string; ids: string[]; collapsible?: boolean }[] = [
  { label: "Benchmark path", ids: ["worker", "openai", "rag", "pgvector", "ollama", "gpu-0", "operator"] },
  { label: "Lane cluster", ids: ["profile:minh-lane", "node:minh-lane", "ns:default", "fixture:pod", "fixture:svc", "fixture:ep", "pod:curl-pod", "pod:tmpcurl", "ns:kube-system", "sys:kube-apiserver", "sys:etcd"] },
  { label: "Host", ids: ["host", "docker", "gpu-1"] },
  { label: "Other profiles", ids: ["profile:minikube", "profile:minh", "profile:lamap", "profile:xyz"], collapsible: true },
];

const LABELS: Record<string, string> = {
  "fixture:pod": "Fixture pod",
  "fixture:svc": "Fixture Service",
  "fixture:ep": "Fixture Endpoints",
  "sys:kube-apiserver": "kube-apiserver",
  "sys:etcd": "etcd",
  "node:minh-lane": "Node minh-lane",
  "profile:minh-lane": "Profile minh-lane",
  "ns:default": "default",
  "ns:kube-system": "kube-system",
};

type CellLook = "future" | "absent" | Health | "active";

function lookOf(state: NodeState | undefined, elapsed: boolean): CellLook {
  if (!elapsed) return "future";
  if (!state) return "absent";
  const health = state.rollup ?? state.health;
  if (state.active && health === "healthy") return "active";
  return health;
}

const CELL: Record<CellLook, string> = {
  future: "bg-track",
  absent: "",
  active: "bg-accent",
  healthy: "bg-fg/25",
  degraded: "bg-warn/55",
  failing: "bg-warn",
  "expected-broken": "hatch bg-fg/10",
  leftover: "bg-warn/25",
  stopped: "after:absolute after:inset-x-0 after:top-1/2 after:h-0.5 after:-translate-y-1/2 after:bg-fg-3/45",
  unknown: "after:absolute after:inset-x-0 after:top-1/2 after:h-px after:-translate-y-1/2 after:bg-fg-3/35",
};

const Cells = memo(function Cells({ row, columns, elapsed, current, selectedCol, groups }: { row: string; columns: PhaseColumn[]; elapsed: number; current: number; selectedCol: number | null; groups: number[][] }) {
  return (
    <div className="flex min-w-0 flex-1 gap-[3px]">
      {groups.map((indices) => (
        <div key={indices[0]} className="flex min-w-0 flex-1 gap-px">
          {indices.map((c) => {
            const look = lookOf(columns[c].states.get(row), c < elapsed);
            return (
              <span
                key={c}
                data-cell={`${row}|${c}`}
                className={clsx(
                  "relative h-[18px] min-w-0 flex-1 rounded-[2px]",
                  CELL[look],
                  c === current && "outline outline-1 -outline-offset-1 outline-accent",
                  c === selectedCol && "z-10 outline-2 outline-offset-1 outline-fg",
                )}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
});

function Legend() {
  const items: { look: CellLook; label: string }[] = [
    { look: "healthy", label: "Healthy" },
    { look: "active", label: "Carrying traffic" },
    { look: "expected-broken", label: "Expected broken" },
    { look: "leftover", label: "Leftover" },
    { look: "degraded", label: "Degraded" },
    { look: "failing", label: "Failing" },
    { look: "stopped", label: "Stopped" },
    { look: "unknown", label: "Unknown" },
    { look: "future", label: "Not yet" },
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[11.5px] text-fg-3">
      {items.map((item) => (
        <span key={item.look} className="inline-flex items-center gap-1.5">
          <span className={clsx("relative inline-block h-3 w-2.5 rounded-[2px]", CELL[item.look])} aria-hidden />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export default function HealthTimeline() {
  const { graph } = useGraph();
  const { campaign, t, seek } = useReplay();
  const [rowsMode, setRowsMode] = useState<"all" | "changed" | "attention">("all");
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [selection, setSelection] = useState<{ row: string; col: number | null }>({ row: "fixture:pod", col: null });
  const [whatIfOn, setWhatIfOn] = useState(false);
  const [hover, setHover] = useState<{ row: string; col: number; x: number; y: number } | null>(null);
  const area = useRef<HTMLDivElement>(null);

  const columns = useMemo(() => (campaign ? phaseColumns(campaign) : []), [campaign]);
  const groups = useMemo(() => {
    const out: number[][] = [];
    columns.forEach((col, i) => {
      const last = out[out.length - 1];
      if (last && columns[last[0]].attempt.index === col.attempt.index) last.push(i);
      else out.push([i]);
    });
    return out;
  }, [columns]);
  const elapsed = columns.filter((c) => c.phase.start <= t).length;
  const current = columns.findIndex((c) => t >= c.phase.start && t < c.phase.end);

  const rowStats = useMemo(() => {
    const stats = new Map<string, { changed: boolean; attention: boolean }>();
    for (const g of GROUPS) {
      for (const id of g.ids) {
        const seen = new Set<string>();
        let attention = false;
        for (let c = 0; c < elapsed; c++) {
          const s = columns[c].states.get(id);
          if (!s) continue;
          seen.add(`${s.rollup ?? s.health}|${s.status}`);
          if (HEALTH[s.rollup ?? s.health].attention) attention = true;
        }
        stats.set(id, { changed: seen.size > 1, attention });
      }
    }
    return stats;
  }, [columns, elapsed]);

  // Moments when something needed attention that wasn't a standing condition.
  const moments = useMemo(() => {
    const standing = new Set<string>();
    for (const g of GROUPS) for (const id of g.ids) if (columns.slice(0, elapsed).every((c) => HEALTH[(c.states.get(id)?.rollup ?? c.states.get(id)?.health) ?? "healthy"].attention)) standing.add(id);
    const out: { col: number; ids: string[] }[] = [];
    for (let c = 0; c < elapsed; c++) {
      const ids = GROUPS.flatMap((g) => g.ids).filter((id) => {
        const s = columns[c].states.get(id);
        return s && !standing.has(id) && HEALTH[s.rollup ?? s.health].attention;
      });
      if (ids.length) out.push({ col: c, ids });
    }
    return { standing: [...standing], out };
  }, [columns, elapsed]);

  const relations = useMemo(() => {
    const map = new Map<string, "up" | "down">();
    if (!graph) return map;
    for (const id of downstreamAll(graph, selection.row, 3).keys()) map.set(id, "down");
    for (const id of upstreamAll(graph, selection.row, 3).keys()) map.set(id, "up");
    return map;
  }, [graph, selection.row]);

  const pinned = selection.col !== null ? columns[selection.col] : undefined;
  const pinnedGraph = useMemo(() => (campaign && pinned ? graphAt(campaign, (pinned.phase.start + pinned.phase.end) / 2) : undefined), [campaign, pinned]);
  const shownGraph = pinnedGraph ?? graph;
  const impact = useMemo(() => (shownGraph && whatIfOn && shownGraph.byId.has(selection.row) ? whatIf(shownGraph, selection.row) : undefined), [shownGraph, whatIfOn, selection.row]);

  if (!graph || !campaign) return <StageFallback />;

  const visibleRows: RowDef[] = GROUPS.flatMap((g) =>
    g.ids
      .filter(() => !g.collapsible || openGroups.has(g.label) || rowsMode !== "all")
      .filter((id) => rowsMode === "all" || (rowsMode === "changed" ? rowStats.get(id)?.changed : rowStats.get(id)?.attention))
      .map((id) => ({ id, group: g.label })),
  );

  const cellFromEvent = (event: MouseEvent<HTMLDivElement>) => {
    const el = (event.target as HTMLElement).closest<HTMLElement>("[data-cell]");
    if (!el) return null;
    const [row, col] = el.dataset.cell!.split("|");
    return { row, col: Number(col), el };
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const rowIndex = visibleRows.findIndex((r) => r.id === selection.row);
    const col = selection.col ?? Math.max(0, current >= 0 ? current : elapsed - 1);
    const moves: Record<string, () => void> = {
      ArrowRight: () => setSelection({ row: selection.row, col: Math.min(Math.max(0, elapsed - 1), col + 1) }),
      ArrowLeft: () => setSelection({ row: selection.row, col: Math.max(0, col - 1) }),
      ArrowDown: () => setSelection({ row: visibleRows[Math.min(visibleRows.length - 1, rowIndex + 1)]?.id ?? selection.row, col }),
      ArrowUp: () => setSelection({ row: visibleRows[Math.max(0, rowIndex - 1)]?.id ?? selection.row, col }),
      Enter: () => pinned && seek((pinned.phase.start + pinned.phase.end) / 2),
      Escape: () => setSelection({ row: selection.row, col: null }),
      w: () => setWhatIfOn((on) => !on),
    };
    if (moves[event.key]) {
      event.preventDefault();
      moves[event.key]();
    }
  };

  const hovered = hover ? { col: columns[hover.col], state: columns[hover.col]?.states.get(hover.row) } : undefined;
  const models = groups.reduce<{ model: string; span: number }[]>((acc, g) => {
    const model = columns[g[0]].attempt.model;
    const last = acc[acc.length - 1];
    if (last && last.model === model) last.span += 1;
    else acc.push({ model, span: 1 });
    return acc;
  }, []);
  const selectedState = pinned?.states.get(selection.row);
  const label = (id: string) => LABELS[id] ?? graph.byId.get(id)?.name ?? columns.find((c) => c.states.get(id))?.states.get(id)?.name ?? id;

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-2 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <DemoTag />
          <LaneHealth graph={graph} />
          <span className="text-[12.5px] text-fg-3">
            {elapsed} of {columns.length} phases elapsed
          </span>
        </div>
        <Segmented
          label="Rows"
          value={rowsMode}
          onChange={setRowsMode}
          options={[
            { value: "all", label: "All rows" },
            { value: "changed", label: "Changed" },
            { value: "attention", label: "Needed attention" },
          ]}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="min-w-0 rounded-lg border border-line bg-surface">
          <header className="grid gap-1 border-b border-line px-4 py-2.5 text-[12.5px]">
            {moments.out.length ? (
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="font-medium text-warn">{moments.out.length} phases with new problems</span>
                {moments.out.slice(0, 3).map((m) => (
                  <button key={m.col} type="button" onClick={() => setSelection({ row: m.ids[0], col: m.col })} className="cursor-pointer text-fg-2 underline decoration-line-strong underline-offset-2 hover:text-fg">
                    attempt {columns[m.col].attempt.index + 1} {columns[m.col].phase.label.toLowerCase()}: {m.ids.map(label).join(", ")}
                  </button>
                ))}
              </div>
            ) : (
              <span className="text-fg-2">No new problems so far in this replay.</span>
            )}
            {moments.standing.length > 0 && <span className="text-fg-3">Standing the whole time: {moments.standing.map(label).join(", ")}.</span>}
          </header>
          <div className="overflow-x-auto">
            <div
              ref={area}
              tabIndex={0}
              role="application"
              aria-label="Health over the replay. Arrow keys move between components and phases, Enter jumps the replay there, W shows what fails, Escape returns to now."
              onKeyDown={onKeyDown}
              onMouseMove={(event) => {
                const hit = cellFromEvent(event);
                if (!hit) return setHover(null);
                const box = area.current!.getBoundingClientRect();
                const cell = hit.el.getBoundingClientRect();
                setHover({ row: hit.row, col: hit.col, x: cell.left - box.left + cell.width / 2, y: cell.top - box.top });
              }}
              onMouseLeave={() => setHover(null)}
              onClick={(event) => {
                const hit = cellFromEvent(event);
                if (hit && hit.col < elapsed) setSelection({ row: hit.row, col: hit.col });
              }}
              className="relative min-w-[760px] px-4 py-3 outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset"
            >
              <div className="flex items-end gap-3 pb-1">
                <div className="sticky left-0 z-10 w-[196px] shrink-0 self-stretch bg-surface" />
                <div className="flex min-w-0 flex-1 gap-[3px]">
                  {models.map((m, i) => (
                    <div key={`${m.model}-${i}`} className="flex min-w-0 items-center gap-1.5 border-b border-line-strong pb-1" style={{ flex: m.span }}>
                      <LabLogo lab={labOf(m.model)} size={12} />
                      <span className="ident truncate text-[11.5px] text-fg-2">{displayModel(m.model)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex items-end gap-3 pb-1.5">
                <div className="label sticky left-0 z-10 w-[196px] shrink-0 bg-surface !text-[10px]">Attempt</div>
                <div className="flex min-w-0 flex-1 gap-[3px]">
                  {groups.map((g) => {
                    const a = columns[g[0]].attempt;
                    const live = g.includes(current);
                    return (
                      <div key={g[0]} className={clsx("num min-w-0 flex-1 truncate text-center text-[10.5px]", live ? "font-medium text-accent" : g[0] < elapsed ? "text-fg-2" : "text-fg-3")} title={`Attempt ${a.index + 1} · ${a.caseId}`}>
                        {a.index + 1}
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="grid gap-[3px]">
                {visibleRows.map((row, i) => {
                  const node = graph.byId.get(row.id);
                  const groupDef = GROUPS.find((g) => g.label === row.group)!;
                  const first = i === 0 || visibleRows[i - 1].group !== row.group;
                  const selected = selection.row === row.id;
                  const relation = relations.get(row.id);
                  const health = node ? (graph.rollups.get(row.id)?.health ?? node.health) : undefined;
                  return (
                    <Fragment key={row.id}>
                      {first && (
                        <div className="flex items-center gap-2 pt-2 pb-0.5">
                          {groupDef.collapsible && rowsMode === "all" ? (
                            <button
                              type="button"
                              aria-expanded={openGroups.has(row.group)}
                              onClick={() => setOpenGroups((s) => new Set(s.has(row.group) ? [...s].filter((x) => x !== row.group) : [...s, row.group]))}
                              className="label inline-flex cursor-pointer items-center gap-1 !text-[10px] hover:!text-fg"
                            >
                              <ChevronRight className="size-3 rotate-90" strokeWidth={2} />
                              {row.group}
                            </button>
                          ) : (
                            <span className="label !text-[10px]">{row.group}</span>
                          )}
                        </div>
                      )}
                      <div className={clsx("flex items-center gap-3 rounded-[4px]", selected && "bg-accent-soft")}>
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => setSelection({ row: row.id, col: null })}
                          className={clsx(
                            "sticky left-0 z-10 flex w-[196px] shrink-0 cursor-pointer items-center gap-1.5 rounded-[4px] bg-surface px-1.5 py-0.5 text-left hover:bg-surface-2",
                            selected && "shadow-[inset_2px_0_0_var(--accent)]",
                          )}
                        >
                          {node ? <NodeIcon node={node} className={clsx("size-3", selected ? "text-accent" : "text-fg-3")} /> : <span className="size-3" />}
                          <span className={clsx("min-w-0 flex-1 truncate text-[12px]", selected ? "text-fg" : "text-fg-2")}>{label(row.id)}</span>
                          {relation && !selected && <span className="shrink-0 text-[10.5px] text-fg-3">{relation === "up" ? "needed" : "needs it"}</span>}
                          {health && <HealthMark health={health} size={9} />}
                        </button>
                        <Cells row={row.id} columns={columns} elapsed={elapsed} current={current} selectedCol={selected ? selection.col : null} groups={groups} />
                      </div>
                    </Fragment>
                  );
                })}
                {visibleRows.length === 0 && <p className="py-6 text-center text-[12.5px] text-fg-3">No rows match.</p>}
              </div>
              {GROUPS.some((g) => g.collapsible && !openGroups.has(g.label)) && rowsMode === "all" && (
                <button type="button" onClick={() => setOpenGroups(new Set(GROUPS.map((g) => g.label)))} className="mt-2 inline-flex cursor-pointer items-center gap-1 text-[12px] text-fg-3 hover:text-fg">
                  <ChevronRight className="size-3" strokeWidth={2} /> Other profiles (4, read-only)
                </button>
              )}
              {hover && hovered?.col && (
                <div
                  className="pointer-events-none absolute z-20 w-60 -translate-x-1/2 -translate-y-full rounded-md bg-surface-2 px-3 py-2 text-[12px] shadow-pop"
                  style={{ left: Math.min(Math.max(hover.x, 130), (area.current?.clientWidth ?? 800) - 130), top: hover.y - 6 }}
                >
                  <div className="truncate font-medium text-fg">{label(hover.row)}</div>
                  <div className="text-fg-3">
                    Attempt {hovered.col.attempt.index + 1} · {hovered.col.phase.label} · {clock(hovered.col.phase.start)}
                  </div>
                  {hover.col >= elapsed ? (
                    <div className="mt-1 text-fg-3">Not reached yet.</div>
                  ) : hovered.state ? (
                    <div className="mt-1 grid gap-0.5">
                      <HealthBadge health={hovered.state.rollup ?? hovered.state.health} />
                      <span className="truncate text-fg-2">{hovered.state.status}</span>
                      {hovered.state.active && <span className="text-accent">Carrying traffic</span>}
                    </div>
                  ) : (
                    <div className="mt-1 text-fg-3">Not present in this case.</div>
                  )}
                </div>
              )}
            </div>
          </div>
          <footer className="grid gap-2 border-t border-line px-4 py-2.5">
            <Legend />
            <p className="text-[11.5px] text-fg-3">Each attempt is six phases: setup, knowledge, debug, verify, Ground Truth, teardown. Click a cell to inspect that moment; arrow keys move once the matrix has focus.</p>
          </footer>
        </section>

        <aside className="min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface xl:sticky xl:top-20 xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto">
          {pinned && pinnedGraph ? (
            <div className="grid content-start gap-3 p-4">
              <div className="grid gap-1">
                <div className="label inline-flex items-center gap-1.5 !text-[10px]">
                  <Clock className="size-3" strokeWidth={2} /> At a past moment
                </div>
                <div className="text-[13px] text-fg">
                  Attempt {pinned.attempt.index + 1} · {pinned.phase.label}
                  <span className="text-fg-3"> · {clock(pinned.phase.start)}</span>
                </div>
                <div className="truncate text-[12px] text-fg-3">
                  {displayModel(pinned.attempt.model)} · {humanize(pinned.attempt.caseId)}
                </div>
              </div>
              {pinnedGraph.byId.get(selection.row) ? (
                <>
                  <div className="grid gap-1 border-t border-line pt-3">
                    <div className="flex items-start gap-1.5">
                      <NodeIcon node={pinnedGraph.byId.get(selection.row)!} className="mt-[3px] text-fg-3" />
                      <span className="font-mono text-[14px] font-medium break-all">{pinnedGraph.byId.get(selection.row)!.name}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-2 text-[12.5px]">
                      <HealthBadge health={selectedState?.rollup ?? selectedState?.health ?? pinnedGraph.byId.get(selection.row)!.health} />
                      <span className="text-fg-3">· {pinnedGraph.byId.get(selection.row)!.status}</span>
                    </div>
                    <p className="text-[12.5px] leading-relaxed text-fg-2">{pinnedGraph.byId.get(selection.row)!.reason}</p>
                  </div>
                  <WhatIfToggle on={whatIfOn} onChange={setWhatIfOn} className="w-full" />
                  {impact && <WhatIfPanel graph={pinnedGraph} impact={impact} onSelect={(id) => setSelection({ row: id, col: selection.col })} />}
                </>
              ) : (
                <p className="border-t border-line pt-3 text-[12.5px] text-fg-3">{label(selection.row)} wasn't present then: this case has no such object.</p>
              )}
              <div className="flex flex-wrap gap-2 border-t border-line pt-3">
                <button
                  type="button"
                  onClick={() => seek((pinned.phase.start + pinned.phase.end) / 2)}
                  className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12px] text-fg hover:bg-surface-2"
                >
                  <CornerDownLeft className="size-3.5" strokeWidth={2} /> Jump replay here
                </button>
                <button type="button" onClick={() => setSelection({ row: selection.row, col: null })} className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2.5 text-[12px] text-fg-2 hover:bg-surface-2 hover:text-fg">
                  <Radio className="size-3.5" strokeWidth={2} /> Back to now
                </button>
              </div>
            </div>
          ) : (
            <Inspector
              graph={graph}
              id={selection.row}
              onSelect={(id) => setSelection({ row: id, col: null })}
              whatIfOn={whatIfOn}
              onWhatIf={setWhatIfOn}
              impact={impact}
              header={
                <div className="label inline-flex items-center gap-1.5 !text-[10px]">
                  <Radio className="size-3 text-accent" strokeWidth={2} /> Now · {clock(t)}
                </div>
              }
            />
          )}
        </aside>
      </div>
      <p className="text-[12px] leading-relaxed text-fg-3">
        Demo state shaped by the lab survey (Nov 1, 2026), sampled at the midpoint of each phase. Health is the lab's state, not a benchmark outcome; fixtures broken by design are hatched, not amber.
      </p>
      <span className="sr-only" aria-live="polite">
        {pinned && selectedState ? `${label(selection.row)}, attempt ${pinned.attempt.index + 1} ${pinned.phase.label}: ${HEALTH_SHORT[selectedState.rollup ?? selectedState.health]}, ${selectedState.status}` : ""}
      </span>
    </div>
  );
}

