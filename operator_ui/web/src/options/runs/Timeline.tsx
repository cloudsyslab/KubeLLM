import clsx from "clsx";
import { scaleUtc } from "d3-scale";
import { ArrowUpRight, ChevronLeft, ChevronRight, Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import { HoverCard } from "radix-ui";
import { useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { Link } from "react-router";
import type { RunSource } from "@/api/types";
import { ErrorState, LoadingState } from "@/components/states";
import { Segmented } from "@/components/ui";
import { techniqueLabel } from "@/lib/explore";
import { count, duration, pct, runDate, usd } from "@/lib/format";
import {
  CompareTray,
  gtTip,
  IncompleteTag,
  RateBar,
  RunModel,
  SelectBox,
  SOURCE_LABEL,
  techniqueShort,
  useRunSelection,
  useRunViews,
  useWidth,
  type RunSelection,
  type RunView,
} from "./shared";

type Range = [number, number];

const HOUR = 3_600_000;
const MIN_SPAN = HOUR;
const LANE_H = 76;
const Y_TOP = 12; // 100% Ground Truth
const Y_ZERO = 52; // 0%
const Y_UNKNOWN = 64; // no known outcome

const clamp = (value: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, value));
const utc = (t: number, options: Intl.DateTimeFormatOptions) => new Date(t).toLocaleString("en-US", { timeZone: "UTC", ...options });

function rangeLabel([a, b]: Range) {
  const sameDay = utc(a, { dateStyle: "medium" }) === utc(b, { dateStyle: "medium" });
  if (sameDay) return `${utc(a, { month: "short", day: "numeric", year: "numeric" })}, ${utc(a, { hour: "2-digit", minute: "2-digit", hour12: false })}–${utc(b, { hour: "2-digit", minute: "2-digit", hour12: false })} UTC`;
  return `${utc(a, { month: "short", day: "numeric" })} – ${utc(b, { month: "short", day: "numeric", year: "numeric" })}`;
}

function tickLabel(t: number, span: number) {
  if (span > 3 * 24 * HOUR) return utc(t, { month: "short", day: "numeric" });
  if (span > 30 * HOUR) return utc(t, { month: "short", day: "numeric", hour: "2-digit", hour12: false }) + "h";
  return utc(t, { hour: "2-digit", minute: "2-digit", hour12: false });
}

function RunCardBody({ view }: { view: RunView }) {
  const { run } = view;
  return (
    <div className="grid gap-3">
      <div>
        <div className="flex items-center gap-2">
          <RunModel view={view} link={false} />
        </div>
        <div className="mt-1 text-[12.5px] text-fg-2">
          {runDate(run.run_id)} UTC · {techniqueLabel(run.technique)} · {SOURCE_LABEL[run.source].toLowerCase()}
        </div>
        <div className="ident mt-0.5 text-[11px] text-fg-3">{run.run_id}</div>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12.5px]">
        <div>
          <dt className="label !text-[10px]">Ground Truth</dt>
          <dd className="num mt-0.5 text-fg">
            <span className="font-medium">{pct(run.ground_truth_rate)}</span>{" "}
            <span className="text-fg-3">
              {run.ground_truth_passed}/{run.ground_truth_known} known
            </span>
          </dd>
        </div>
        <div>
          <dt className="label !text-[10px]">Unknown</dt>
          <dd className={clsx("num mt-0.5", run.ground_truth_unavailable ? "text-warn" : "text-fg-2")}>{run.ground_truth_unavailable}</dd>
        </div>
        <div>
          <dt className="label !text-[10px]">Verifier agrees</dt>
          <dd className="num mt-0.5 text-fg-2">{pct(view.verifierRate, 0)}</dd>
        </div>
        <div>
          <dt className="label !text-[10px]">Cases</dt>
          <dd className="num mt-0.5 text-fg-2">
            {run.observed_cases}/{run.planned_cases}
          </dd>
        </div>
        <div>
          <dt className="label !text-[10px]">Duration</dt>
          <dd className="num mt-0.5 text-fg-2">{duration(run.duration_s)}</dd>
        </div>
        <div>
          <dt className="label !text-[10px]">Cost</dt>
          <dd className="num mt-0.5 text-fg-2">{usd(run.total_cost)}</dd>
        </div>
      </dl>
      {run.status === "incomplete" && (
        <p className="text-[12px] text-warn">
          Incomplete: {run.ground_truth_unavailable} unknown {run.ground_truth_unavailable === 1 ? "outcome" : "outcomes"}
          {view.missing ? `, ${view.missing} planned ${view.missing === 1 ? "case" : "cases"} not recorded` : ""}.
        </p>
      )}
    </div>
  );
}

function RunMark({
  view,
  left,
  width,
  selection,
  hovered,
  onHover,
  showLabel,
}: {
  view: RunView;
  left: number;
  width: number;
  selection: RunSelection;
  hovered: boolean;
  onHover: (ref: string | null) => void;
  showLabel: boolean;
}) {
  const { run } = view;
  const on = selection.has(view.ref);
  const rate = run.ground_truth_rate;
  const top = rate === null ? Y_UNKNOWN : Y_ZERO - rate * (Y_ZERO - Y_TOP);
  return (
    <HoverCard.Root openDelay={180} closeDelay={60}>
      <HoverCard.Trigger asChild>
        <button
          type="button"
          aria-pressed={on}
          aria-label={`${view.debug}, ${runDate(run.run_id)}: Ground Truth ${pct(rate)}${run.ground_truth_unavailable ? `, ${run.ground_truth_unavailable} unknown` : ""}. ${on ? "Selected for comparison" : "Select for comparison"}`}
          onClick={() => selection.toggle(view.ref)}
          onMouseEnter={() => onHover(view.ref)}
          onMouseLeave={() => onHover(null)}
          onFocus={() => onHover(view.ref)}
          onBlur={() => onHover(null)}
          className={clsx(
            "absolute z-[1] h-2 -translate-y-1/2 cursor-pointer rounded-full transition-[box-shadow,background-color] duration-100 focus-visible:z-[3]",
            rate === null ? "hatch border border-line-strong" : on ? "bg-accent" : "bg-fg-2 hover:bg-fg",
            run.status === "incomplete" && !on && "outline outline-1 outline-offset-1 outline-warn/80",
            (hovered || on) && "z-[2]",
            hovered && "ring-2 ring-accent ring-offset-1 ring-offset-surface",
          )}
          style={{ left: `${left}%`, width: `max(8px, ${width}%)`, top }}
        >
          {showLabel && rate !== null && (
            <span className={clsx("num pointer-events-none absolute bottom-full left-0 mb-0.5 text-[10.5px] leading-none whitespace-nowrap", on ? "text-accent" : "text-fg-3")}>{pct(rate, 0)}</span>
          )}
        </button>
      </HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content side="top" align="center" sideOffset={8} collisionPadding={12} className="z-50 w-[300px] rounded-lg bg-surface-2 p-4 shadow-pop">
          <RunCardBody view={view} />
          <div className="mt-3 flex items-center gap-3 border-t border-line pt-3 text-[12.5px]">
            <span className="text-fg-3">{on ? "Selected · click to remove" : selection.full ? "Compare holds 8 runs" : "Click to select"}</span>
            <Link to={`/runs/${view.ref}`} className="ml-auto inline-flex items-center gap-1 text-fg-2 hover:text-fg">
              Open run <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
            </Link>
          </div>
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}

// Overview of the full history with a draggable window: drag the window to
// pan, its edges to resize, or empty track to draw a new one.
function Brush({ full, win, setWin, views, selection }: { full: Range; win: Range; setWin: (next: Range) => void; views: RunView[]; selection: RunSelection }) {
  const ref = useRef<HTMLDivElement>(null);
  const drag = useRef<{ mode: "move" | "left" | "right" | "new"; anchor: number; start: Range; moved: boolean } | null>(null);
  const span = full[1] - full[0];
  const x = (t: number) => ((t - full[0]) / span) * 100;
  const toTime = (clientX: number) => {
    const rect = ref.current!.getBoundingClientRect();
    return full[0] + clamp((clientX - rect.left) / rect.width, 0, 1) * span;
  };
  const fit = (a: number, b: number): Range => {
    let lo = Math.min(a, b);
    let hi = Math.max(a, b);
    if (hi - lo < MIN_SPAN) hi = lo + MIN_SPAN;
    if (hi > full[1]) [lo, hi] = [full[1] - (hi - lo), full[1]];
    if (lo < full[0]) [lo, hi] = [full[0], full[0] + (hi - lo)];
    return [lo, Math.min(hi, full[1])];
  };

  const onDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const mode = ((event.target as HTMLElement).dataset.brush as "move" | "left" | "right" | undefined) ?? "new";
    const t = toTime(event.clientX);
    drag.current = { mode, anchor: t, start: win, moved: false };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  };
  const onMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d) return;
    const t = toTime(event.clientX);
    const [a, b] = d.start;
    if (Math.abs(t - d.anchor) > span * 0.004) d.moved = true;
    if (!d.moved) return;
    if (d.mode === "move") {
      const shift = clamp(t - d.anchor, full[0] - a, full[1] - b);
      setWin([a + shift, b + shift]);
    } else if (d.mode === "left") setWin([Math.min(t, b - MIN_SPAN), b]);
    else if (d.mode === "right") setWin([a, Math.max(t, a + MIN_SPAN)]);
    else setWin(fit(d.anchor, t));
  };
  const onUp = () => {
    const d = drag.current;
    drag.current = null;
    // A click on the track recentres the current window there.
    if (d?.mode === "new" && !d.moved) {
      const half = (d.start[1] - d.start[0]) / 2;
      setWin(fit(d.anchor - half, d.anchor + half));
    }
  };
  const onKey = (event: ReactKeyboardEvent) => {
    const w = win[1] - win[0];
    const map: Record<string, () => Range> = {
      ArrowLeft: () => fit(win[0] - w * 0.2, win[1] - w * 0.2),
      ArrowRight: () => fit(win[0] + w * 0.2, win[1] + w * 0.2),
      "+": () => fit(win[0] + w * 0.25, win[1] - w * 0.25),
      "=": () => fit(win[0] + w * 0.25, win[1] - w * 0.25),
      "-": () => fit(win[0] - w * 0.5, win[1] + w * 0.5),
      Home: () => full,
    };
    if (map[event.key]) {
      event.preventDefault();
      setWin(map[event.key]());
    }
  };

  return (
    <div
      ref={ref}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      className="relative h-10 cursor-crosshair touch-none rounded-md bg-surface-2 select-none"
    >
      {views.map((view) => (
        <span
          key={view.ref}
          aria-hidden
          className={clsx("pointer-events-none absolute top-2 bottom-2 w-px", selection.has(view.ref) ? "bg-accent" : "bg-fg-3/60")}
          style={{ left: `${x(view.at!)}%` }}
        />
      ))}
      <div
        tabIndex={0}
        role="group"
        aria-label={`Visible range ${rangeLabel(win)}. Arrow keys pan, plus and minus zoom, Home shows everything.`}
        onKeyDown={onKey}
        data-brush="move"
        className="absolute inset-y-0 cursor-grab rounded-md border border-accent-line bg-accent-soft active:cursor-grabbing"
        style={{ left: `${x(win[0])}%`, width: `max(6px, ${x(win[1]) - x(win[0])}%)` }}
      >
        <span data-brush="left" aria-hidden className="absolute inset-y-0 -left-1 w-2.5 cursor-ew-resize">
          <span data-brush="left" className="absolute top-1/2 left-1/2 h-4 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent" />
        </span>
        <span data-brush="right" aria-hidden className="absolute inset-y-0 -right-1 w-2.5 cursor-ew-resize">
          <span data-brush="right" className="absolute top-1/2 left-1/2 h-4 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent" />
        </span>
      </div>
    </div>
  );
}

interface Lane {
  model: string;
  views: RunView[];
  label: RunView;
}

function IconButton({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
      className="grid size-8 cursor-pointer place-items-center rounded-md border border-line bg-surface text-fg-2 hover:bg-surface-2 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  );
}

export default function Timeline() {
  const { views, byRef, isLoading, error } = useRunViews();
  const selection = useRunSelection();
  const [source, setSource] = useState<"all" | RunSource>("all");
  const [hovered, setHovered] = useState<string | null>(null);
  const [listLimit, setListLimit] = useState(12);
  const [plotRef, plotWidth] = useWidth();

  const timed = useMemo(() => views.filter((v) => v.at !== null && (source === "all" || v.run.source === source)), [views, source]);
  const full = useMemo<Range>(() => {
    if (!timed.length) return [0, 1];
    const lo = Math.min(...timed.map((v) => v.at!));
    const hi = Math.max(...timed.map((v) => v.end!));
    const pad = Math.max((hi - lo) * 0.015, HOUR);
    return [lo - pad, hi + pad];
  }, [timed]);
  const [win, setWinState] = useState<Range | null>(null);
  const range: Range = win ? [clamp(win[0], full[0], full[1]), clamp(win[1], full[0], full[1])] : full;
  const setWin = (next: Range) => setWinState(next[0] <= full[0] && next[1] >= full[1] ? null : next);

  const lanes = useMemo<Lane[]>(() => {
    const groups = new Map<string, RunView[]>();
    for (const view of timed) groups.set(view.debug, [...(groups.get(view.debug) ?? []), view]);
    return [...groups.entries()]
      .map(([model, members]) => {
        const sorted = [...members].sort((a, b) => a.at! - b.at!);
        return { model, views: sorted, label: sorted.find((v) => v.run.source === "canonical") ?? sorted[sorted.length - 1] };
      })
      .sort((a, b) => (a.model === "unrecorded" ? 1 : b.model === "unrecorded" ? -1 : a.views[0].at! - b.views[0].at!));
  }, [timed]);

  const months = useMemo(() => {
    const groups = new Map<string, RunView[]>();
    for (const view of timed) {
      const key = utc(view.at!, { year: "numeric", month: "2-digit" });
      groups.set(key, [...(groups.get(key) ?? []), view]);
    }
    return [...groups.values()]
      .map((members) => {
        const lo = Math.min(...members.map((v) => v.at!));
        const hi = Math.max(...members.map((v) => v.end!));
        const pad = Math.max((hi - lo) * 0.04, HOUR);
        return { label: utc(lo, { month: "short" }), count: members.length, range: [lo - pad, hi + pad] as Range };
      })
      .sort((a, b) => a.range[0] - b.range[0]);
  }, [timed]);

  if (isLoading) return <LoadingState label="Reading recorded runs" />;
  if (error) return <ErrorState error={error} />;

  const span = range[1] - range[0];
  const x = (t: number) => ((t - range[0]) / span) * 100;
  const inView = timed.filter((v) => v.end! >= range[0] && v.at! <= range[1]).sort((a, b) => b.at! - a.at!);
  const ticks = scaleUtc()
    .domain(range)
    .ticks(Math.max(2, Math.floor((plotWidth || 800) / 120)))
    .map((d) => d.getTime());
  const zoom = (factor: number) => {
    const mid = (range[0] + range[1]) / 2;
    const half = Math.max(MIN_SPAN / 2, (span * factor) / 2);
    const lo = clamp(mid - half, full[0], full[1] - 2 * half);
    setWin([lo, Math.min(full[1], lo + 2 * half)]);
  };
  const pan = (dir: number) => {
    const shift = clamp(span * 0.3 * dir, full[0] - range[0], full[1] - range[1]);
    setWin([range[0] + shift, range[1] + shift]);
  };
  const pxPerMs = plotWidth / span;

  return (
    <div className="grid gap-4">
      <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Runs over time">
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-3 sm:px-4">
          <Segmented
            label="Source"
            value={source}
            onChange={(next) => {
              setSource(next);
              setWinState(null);
            }}
            options={[
              { value: "all", label: "All" },
              ...(["canonical", "exploratory", "local"] as RunSource[]).filter((s) => views.some((v) => v.run.source === s)).map((s) => ({ value: s, label: SOURCE_LABEL[s] })),
            ]}
          />
          <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Jump to a month">
            {months.map((month) => {
              const active = win !== null && Math.abs(range[0] - month.range[0]) < 1000 && Math.abs(range[1] - month.range[1]) < 1000;
              return (
                <button
                  key={month.label + month.range[0]}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setWin(month.range)}
                  className={clsx(
                    "inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md px-2 text-[12.5px] transition-colors",
                    active ? "bg-surface-3 text-fg" : "text-fg-3 hover:bg-surface-2 hover:text-fg",
                  )}
                >
                  {month.label}
                  <span className="num text-[11px] text-fg-3">{month.count}</span>
                </button>
              );
            })}
          </div>
          <div className="ml-auto flex items-center gap-1">
            <IconButton label="Pan earlier" onClick={() => pan(-1)} disabled={range[0] <= full[0]}>
              <ChevronLeft className="size-4" strokeWidth={1.75} />
            </IconButton>
            <IconButton label="Pan later" onClick={() => pan(1)} disabled={range[1] >= full[1]}>
              <ChevronRight className="size-4" strokeWidth={1.75} />
            </IconButton>
            <IconButton label="Zoom in" onClick={() => zoom(0.5)} disabled={span <= MIN_SPAN * 1.01}>
              <ZoomIn className="size-4" strokeWidth={1.75} />
            </IconButton>
            <IconButton label="Zoom out" onClick={() => zoom(2)} disabled={!win}>
              <ZoomOut className="size-4" strokeWidth={1.75} />
            </IconButton>
            <IconButton label="Show all time" onClick={() => setWinState(null)} disabled={!win}>
              <Maximize2 className="size-3.5" strokeWidth={1.75} />
            </IconButton>
          </div>
        </div>

        <div className="relative overflow-x-auto">
          <div className="min-w-[720px]">
            <div className="grid grid-cols-[128px_minmax(0,1fr)] sm:grid-cols-[172px_minmax(0,1fr)] items-center gap-y-1.5 border-b border-line py-3 pr-4">
              <div className="sticky left-0 z-10 bg-surface pl-4">
                <div className="label !text-[10px]">Overview</div>
              </div>
              <Brush full={full} win={range} setWin={setWin} views={timed} selection={selection} />
              <div className="sticky left-0 z-10 bg-surface pl-4">
                <div className="label !text-[10px]">In view</div>
              </div>
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-[12.5px]">
                <span className="text-fg">{rangeLabel(range)}</span>
                <span className="num text-fg-3">
                  {count(inView.length)} of {count(timed.length)} runs
                </span>
              </div>
            </div>

            <div className="grid grid-cols-[128px_minmax(0,1fr)] sm:grid-cols-[172px_minmax(0,1fr)] pr-4">
              <div className="sticky left-0 z-10 bg-surface" />
              <div ref={plotRef} className="relative h-7">
                {ticks.map((t) => (
                  <span key={t} className="num absolute bottom-1.5 -translate-x-1/2 text-[11px] whitespace-nowrap text-fg-3" style={{ left: `${x(t)}%` }}>
                    {tickLabel(t, span)}
                  </span>
                ))}
              </div>
            </div>

            <div className="pb-2">
              {lanes.map((lane) => {
                const visible = lane.views.filter((v) => v.end! >= range[0] && v.at! <= range[1]);
                // Lanes with nothing in the window collapse so the active ones stay close together.
                const empty = visible.length === 0;
                return (
                  <div key={lane.model} className="group/lane grid grid-cols-[128px_minmax(0,1fr)] sm:grid-cols-[172px_minmax(0,1fr)] border-t border-line pr-4">
                    <div className={clsx("sticky left-0 z-10 flex min-w-0 border-r border-line bg-surface pr-3 pl-4", empty ? "items-center gap-2 py-1" : "flex-col justify-center gap-0.5 py-2")}>
                      <RunModel view={lane.label} className={clsx("text-[12.5px]", empty && "opacity-60")} />
                      <span className={clsx("num text-[11.5px] text-fg-3", empty ? "ml-auto shrink-0" : "pl-[21px]")}>
                        {empty ? `0/${lane.views.length}` : `${visible.length}/${lane.views.length} in view`}
                      </span>
                    </div>
                    {empty ? (
                      <div className="relative h-8">
                        {ticks.map((t) => (
                          <span key={t} aria-hidden className="absolute inset-y-0 w-px bg-[var(--grid)]" style={{ left: `${x(t)}%` }} />
                        ))}
                      </div>
                    ) : (
                    <div className="relative overflow-hidden" style={{ height: LANE_H }}>
                      {ticks.map((t) => (
                        <span key={t} aria-hidden className="absolute inset-y-0 w-px bg-[var(--grid)]" style={{ left: `${x(t)}%` }} />
                      ))}
                      {[Y_TOP, (Y_TOP + Y_ZERO) / 2, Y_ZERO].map((y, i) => (
                        <span key={y} aria-hidden className={clsx("absolute inset-x-0 h-px", i === 1 ? "bg-[var(--grid)]" : "bg-line")} style={{ top: y }} />
                      ))}
                      <span aria-hidden className="label pointer-events-none absolute right-1 !text-[9px] opacity-0 transition-opacity group-hover/lane:opacity-100" style={{ top: Y_TOP - 10 }}>
                        100%
                      </span>
                      <span aria-hidden className="label pointer-events-none absolute right-1 !text-[9px] opacity-0 transition-opacity group-hover/lane:opacity-100" style={{ top: Y_ZERO - 10 }}>
                        0%
                      </span>
                      {visible.map((view) => {
                        const left = clamp(x(view.at!), -2, 102);
                        const right = clamp(x(view.end!), -2, 102);
                        const widthPx = (view.end! - view.at!) * pxPerMs;
                        return (
                          <RunMark
                            key={view.ref}
                            view={view}
                            left={left}
                            width={Math.max(0, right - left)}
                            selection={selection}
                            hovered={hovered === view.ref}
                            onHover={setHovered}
                            showLabel={Math.max(widthPx, 8) >= 34}
                          />
                        );
                      })}
                    </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-5 rounded-full bg-fg-2" /> Run: length is duration, height is Ground Truth success
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="hatch h-2 w-5 rounded-full border border-line-strong" /> No known outcome
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-5 rounded-full bg-fg-2 outline outline-1 outline-offset-1 outline-warn/80" /> Incomplete
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-5 rounded-full bg-accent" /> Selected
          </span>
          <span className="sm:ml-auto">Times in UTC. Click a run to select it; drag the overview to zoom.</span>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Runs in view">
        <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-4 py-3">
          <h2 className="text-[13.5px] font-medium">Runs in view</h2>
          <span className="text-[12.5px] text-fg-3">Newest first · tick to compare</span>
        </header>
        <ul className="divide-y divide-line" onMouseLeave={() => setHovered(null)}>
          {inView.slice(0, listLimit).map((view) => {
            const { run } = view;
            const on = selection.has(view.ref);
            return (
              <li
                key={view.ref}
                onMouseEnter={() => setHovered(view.ref)}
                className={clsx(
                  "grid grid-cols-[20px_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2 text-[13px] transition-colors sm:grid-cols-[20px_190px_minmax(0,1fr)_150px_150px_72px_72px]",
                  on ? "bg-accent-soft" : hovered === view.ref ? "bg-surface-2/60" : "",
                )}
              >
                <SelectBox checked={on} disabled={selection.full} onChange={() => selection.toggle(view.ref)} label={`Select run ${run.run_id} of ${view.debug} for comparison`} />
                <div className="grid min-w-0 gap-0.5">
                  <span className="flex min-w-0 items-center gap-2">
                    <Link to={`/runs/${view.ref}`} className="truncate text-fg hover:underline hover:decoration-line-strong hover:underline-offset-2">
                      {runDate(run.run_id)}
                    </Link>
                    {run.status === "incomplete" && <IncompleteTag run={run} />}
                  </span>
                  <span className="min-w-0 sm:hidden">
                    <RunModel view={view} className="text-[12.5px]" />
                  </span>
                </div>
                <span className="hidden min-w-0 sm:block">
                  <RunModel view={view} className="text-[12.5px]" />
                </span>
                <span className="hidden truncate text-[12.5px] text-fg-3 sm:block" title={techniqueLabel(run.technique)}>
                  {techniqueShort(run.technique)} · {SOURCE_LABEL[run.source].toLowerCase()}
                </span>
                <span className="inline-flex items-center justify-end gap-2 sm:justify-start" title={gtTip(run)}>
                  <RateBar rate={run.ground_truth_rate} width={44} active={on} />
                  <span className="num w-11 text-right font-medium">{pct(run.ground_truth_rate)}</span>
                </span>
                <span className="num hidden text-right text-fg-2 sm:block">{duration(run.duration_s)}</span>
                <span className="num hidden text-right text-fg-2 sm:block">{usd(run.total_cost)}</span>
              </li>
            );
          })}
        </ul>
        {inView.length > listLimit && (
          <button type="button" onClick={() => setListLimit(inView.length)} className="w-full cursor-pointer border-t border-line px-4 py-2.5 text-left text-[12.5px] text-fg-3 hover:text-fg">
            Show all {inView.length} runs in view
          </button>
        )}
        {inView.length === 0 && <p className="px-4 py-8 text-center text-[13px] text-fg-3">No runs in this window. Widen it in the overview.</p>}
      </section>

      <CompareTray selection={selection} byRef={byRef} />
    </div>
  );
}
