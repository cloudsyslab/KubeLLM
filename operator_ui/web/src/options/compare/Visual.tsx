import clsx from "clsx";
import { max, min, quantile } from "d3-array";
import { scaleLinear } from "d3-scale";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useState, type CSSProperties, type ReactNode } from "react";
import { FamilyCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { ErrorState } from "@/components/states";
import { Tip } from "@/components/ui";
import { groupCases, humanize } from "@/lib/cases";
import { compact, duration, pct, runDate, usd } from "@/lib/format";
import { useWidth, type RunView } from "../runs/shared";
import { rowsOf, sideStats, stateOf, type SideStats } from "./model";
import { AlignmentPanel, CompareLoading, CompareNotice, RunHead, RunMarker, RunPicker, ScopeToggle, useCompare, type CompareState } from "./shared";

type Hover = number | null;

// 95% Wilson score interval for a pass rate over n known attempts.
function wilson(passed: number, n: number, z = 1.96): [number, number] | null {
  if (!n) return null;
  const p = passed / n;
  const d = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / d;
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}

function attemptTimes(view: RunView, cases: string[] | null): number[] {
  const rows = rowsOf(view.run);
  const ids = cases ?? [...rows.keys()];
  return ids
    .map((id) => rows.get(id)?.duration_s)
    .filter((v): v is number => typeof v === "number")
    .sort((a, b) => a - b);
}

interface Focus {
  hover: Hover;
  setHover: (h: Hover) => void;
  pinned: Hover;
  pin: (h: Hover) => void;
}

// Hover follows the pointer; a click pins a run so touch screens can follow it too.
function Marker({ index, focus, label, tip, style, className }: { index: number; focus: Focus; label: string; tip: ReactNode; style: CSSProperties; className?: string }) {
  const { hover, setHover } = focus;
  const dim = hover !== null && hover !== index;
  return (
    <Tip content={tip}>
      <button
        type="button"
        aria-label={label}
        aria-pressed={focus.pinned === index}
        onClick={() => focus.pin(focus.pinned === index ? null : index)}
        onMouseEnter={() => setHover(index)}
        onMouseLeave={() => setHover(null)}
        onFocus={() => setHover(index)}
        onBlur={() => setHover(null)}
        className={clsx(
          "absolute grid size-[20px] -translate-x-1/2 -translate-y-1/2 cursor-pointer place-items-center rounded-full border font-mono text-[10.5px] font-medium transition-[opacity,box-shadow] duration-100",
          index === 0 ? "border-accent bg-accent text-accent-ink" : "border-line-strong bg-surface-3 text-fg",
          hover === index && "z-10 ring-2 ring-accent ring-offset-2 ring-offset-surface",
          dim && "opacity-30",
          className,
        )}
        style={style}
      >
        {index + 1}
      </button>
    </Tip>
  );
}

interface StripMetric {
  key: string;
  label: string;
  better: "higher" | "lower";
  value: (s: SideStats) => number | null;
  format: (v: number) => string;
  axis: (v: number) => string;
  domain: (values: number[]) => [number, number];
  detail: (s: SideStats) => string;
}

const STRIPS: StripMetric[] = [
  { key: "gt", label: "Ground Truth success", better: "higher", value: (s) => s.rate, format: (v) => pct(v), axis: (v) => pct(v, 0), domain: () => [0, 1], detail: (s) => `${s.passed} of ${s.known} known${s.unknown ? `, ${s.unknown} unknown` : ""}` },
  { key: "verifier", label: "Verifier agrees", better: "higher", value: (s) => s.verifyRate, format: (v) => pct(v, 0), axis: (v) => pct(v, 0), domain: () => [0, 1], detail: (s) => `${s.verifyCorrect} of ${s.verifyComparable} comparable` },
  { key: "time", label: "Time per attempt", better: "lower", value: (s) => s.medianTime, format: duration, axis: duration, domain: (v) => [0, (max(v) ?? 1) * 1.12], detail: (s) => `Median of ${s.attempts} attempts` },
  { key: "cost", label: "Cost per attempt", better: "lower", value: (s) => s.costPerAttempt, format: usd, axis: usd, domain: (v) => [0, (max(v) ?? 1) * 1.12], detail: (s) => `${s.costRows} of ${s.attempts} attempts recorded cost` },
  { key: "tokens", label: "Tokens per attempt", better: "lower", value: (s) => s.tokensPerAttempt, format: compact, axis: compact, domain: (v) => [0, (max(v) ?? 1) * 1.12], detail: (s) => `${s.tokenRows} of ${s.attempts} attempts recorded tokens` },
];

// Each metric is a line with one numbered marker per run. Markers that would
// overlap stack upward so every run stays visible and focusable.
function MetricStrips({ runs, stats, focus }: { runs: RunView[]; stats: SideStats[]; focus: Focus }) {
  const { hover } = focus;
  const [trackRef, trackWidth] = useWidth();
  // Markers closer than their own width stack upward.
  const near = trackWidth ? (23 / trackWidth) * 100 : 4.2;
  return (
    <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Metrics by run">
      <header className="border-b border-line px-4 py-3">
        <h2 className="text-[13.5px] font-medium">Where each run lands</h2>
        <p className="mt-0.5 text-[12.5px] text-fg-3">One marker per run on each metric. Hover a marker to follow that run through every chart.</p>
      </header>
      <div className="divide-y divide-line">
        {STRIPS.map((metric, metricIndex) => {
          const values = stats.map(metric.value);
          const present = values.filter((v): v is number => v !== null);
          const [lo, hi] = metric.domain(present);
          const pos = (v: number) => ((v - lo) / (hi - lo || 1)) * 100;
          const placed = values
            .map((v, index) => ({ v, index }))
            .filter((p): p is { v: number; index: number } => p.v !== null)
            .sort((a, b) => a.v - b.v);
          const levels: number[] = [];
          let last: { x: number; level: number }[] = [];
          for (const p of placed) {
            const x = pos(p.v);
            let level = 0;
            while (last.some((q) => q.level === level && Math.abs(q.x - x) < near)) level += 1;
            levels[p.index] = level;
            last = [...last.filter((q) => Math.abs(q.x - x) < near), { x, level }];
          }
          const depth = Math.max(0, ...levels.filter((l) => l !== undefined));
          const missing = values.map((v, i) => (v === null ? i : -1)).filter((i) => i >= 0);
          const best = present.length ? (metric.better === "higher" ? Math.max(...present) : Math.min(...present)) : null;
          return (
            <div key={metric.key} className="grid gap-x-6 gap-y-2 px-4 py-3 md:grid-cols-[176px_minmax(0,1fr)]">
              <div className="grid content-start gap-0.5">
                <span className="text-[13px] font-medium">{metric.label}</span>
                <span className="inline-flex items-center gap-1 text-[11.5px] text-fg-3">
                  {metric.better === "higher" ? <ArrowUp className="size-3" strokeWidth={2} /> : <ArrowDown className="size-3" strokeWidth={2} />}
                  {metric.better === "higher" ? "Higher is better" : "Lower is better"}
                </span>
                {hover !== null && values[hover] !== null ? (
                  <span className="num mt-1 text-[12.5px] text-fg">
                    <RunMarker index={hover} size={15} className="mr-1.5 !text-[9.5px] align-[-2px]" />
                    {metric.format(values[hover] as number)}
                  </span>
                ) : (
                  best !== null && (
                    <span className="num mt-1 text-[12px] text-fg-3">
                      Best {metric.format(best)}
                      {present.length > 1 && ` · worst ${metric.format(metric.better === "higher" ? Math.min(...present) : Math.max(...present))}`}
                    </span>
                  )
                )}
              </div>
              <div className="min-w-0">
                <div ref={metricIndex === 0 ? trackRef : undefined} className="relative mx-2.5" style={{ height: 30 + depth * 22 }}>
                  <span aria-hidden className="absolute inset-x-0 h-px bg-line-strong" style={{ bottom: 14 }} />
                  {[0, 0.25, 0.5, 0.75, 1].map((t) => (
                    <span key={t} aria-hidden className="absolute h-2 w-px bg-line-strong" style={{ left: `${t * 100}%`, bottom: 10 }} />
                  ))}
                  {placed.map(({ v, index }) => (
                    <Marker
                      key={index}
                      index={index}
                      focus={focus}
                      label={`Run ${index + 1}, ${runs[index].debug}: ${metric.label} ${metric.format(v)}`}
                      tip={
                        <div className="grid gap-0.5">
                          <div className="text-fg">
                            Run {index + 1} · <span className="ident">{runs[index].debug}</span>
                          </div>
                          <div>
                            {metric.label}: <span className="num font-medium text-fg">{metric.format(v)}</span>
                          </div>
                          <div className="text-fg-3">{metric.detail(stats[index])}</div>
                        </div>
                      }
                      style={{ left: `${pos(v)}%`, bottom: 14 + levels[index] * 22, transform: "translate(-50%, 50%)" }}
                    />
                  ))}
                </div>
                <div className="num mx-2.5 flex justify-between text-[10.5px] text-fg-3">
                  <span>{metric.axis(lo)}</span>
                  <span>{metric.axis((lo + hi) / 2)}</span>
                  <span>{metric.axis(hi)}</span>
                </div>
                {missing.length > 0 && (
                  <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[11.5px] text-fg-3">
                    Not recorded for
                    {missing.map((i) => (
                      <RunMarker key={i} index={i} size={15} className="!text-[9.5px]" />
                    ))}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Scatter({ runs, stats, state, focus }: { runs: RunView[]; stats: SideStats[]; state: CompareState; focus: Focus }) {
  const { hover } = focus;
  const [ref, width] = useWidth();
  const H = 300;
  const M = { t: 26, r: 24, b: 40, l: 52 };
  const W = Math.max(width, 300);
  const points = runs.map((view, index) => {
    const s = stats[index];
    const times = attemptTimes(view, state.casesFor(view));
    return {
      index,
      time: s.medianTime,
      rate: s.rate,
      ci: wilson(s.passed, s.known),
      q1: quantile(times, 0.25) ?? null,
      q3: quantile(times, 0.75) ?? null,
    };
  });
  const plotted = points.filter((p) => p.time !== null && p.rate !== null);
  const xMax = (max(plotted.map((p) => p.q3 ?? p.time ?? 0)) ?? 1) * 1.1 || 1;
  const yMin = Math.max(0, Math.floor(((min(plotted.map((p) => p.ci?.[0] ?? p.rate ?? 0)) ?? 0) - 0.05) * 10) / 10);
  const x = scaleLinear().domain([0, xMax]).nice().range([M.l, W - M.r]);
  const y = scaleLinear().domain([yMin, 1]).range([H - M.b, M.t]);
  const skipped = points.filter((p) => p.time === null || p.rate === null);

  return (
    <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Time against Ground Truth success">
      <header className="border-b border-line px-4 py-3">
        <h2 className="text-[13.5px] font-medium">Time against success</h2>
        <p className="mt-0.5 text-[12.5px] text-fg-3">
          Up and to the left is faster and more successful. Whiskers show the middle half of attempt times and the 95% Wilson interval of the success rate over known attempts.
        </p>
      </header>
      <div ref={ref} className="relative px-0 pt-2" style={{ height: H + 8 }}>
        {width > 0 && (
          <>
            <svg width={W} height={H} className="absolute top-2 left-0" aria-hidden>
              {y.ticks(5).map((t) => (
                <g key={t}>
                  <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
                  <text x={M.l - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={10.5} fill="var(--fg-3)" className="num">
                    {Math.round(t * 100)}%
                  </text>
                </g>
              ))}
              {x.ticks(Math.max(2, Math.floor(W / 110))).map((t) => (
                <g key={t}>
                  <line x1={x(t)} x2={x(t)} y1={M.t} y2={H - M.b} stroke="var(--grid)" />
                  <text x={x(t)} y={H - M.b + 16} textAnchor="middle" fontSize={10.5} fill="var(--fg-3)">
                    {duration(t)}
                  </text>
                </g>
              ))}
              <text x={W - M.r} y={H - 6} textAnchor="end" fontSize={11} fill="var(--fg-3)">
                Median time per attempt →
              </text>
              <text x={M.l} y={M.t - 7} fontSize={11} fill="var(--fg-3)">
                ↑ Ground Truth success
              </text>
              {plotted.map((p) => {
                const dim = hover !== null && hover !== p.index;
                const stroke = p.index === 0 ? "var(--accent)" : "var(--fg-3)";
                return (
                  <g key={p.index} opacity={dim ? 0.25 : 1}>
                    {p.q1 !== null && p.q3 !== null && <line x1={x(p.q1)} x2={x(p.q3)} y1={y(p.rate!)} y2={y(p.rate!)} stroke={stroke} strokeWidth={1.5} strokeLinecap="round" />}
                    {p.ci && <line x1={x(p.time!)} x2={x(p.time!)} y1={y(p.ci[0])} y2={y(p.ci[1])} stroke={stroke} strokeWidth={1.5} strokeLinecap="round" />}
                  </g>
                );
              })}
            </svg>
            {plotted.map((p) => {
              const view = runs[p.index];
              return (
                <Marker
                  key={p.index}
                  index={p.index}
                  focus={focus}
                  label={`Run ${p.index + 1}, ${view.debug}: ${pct(p.rate)} Ground Truth success, ${duration(p.time)} per attempt`}
                  tip={
                    <div className="grid gap-0.5">
                      <div className="text-fg">
                        Run {p.index + 1} · <span className="ident">{view.debug}</span>
                      </div>
                      <div className="text-fg-3">{runDate(view.run.run_id)}</div>
                      <div>
                        Ground Truth <span className="num font-medium text-fg">{pct(p.rate)}</span>
                        {p.ci && (
                          <span className="num text-fg-3">
                            {" "}
                            (95% interval {pct(p.ci[0], 0)}–{pct(p.ci[1], 0)})
                          </span>
                        )}
                      </div>
                      <div>
                        Median <span className="num font-medium text-fg">{duration(p.time)}</span>
                        {p.q1 !== null && p.q3 !== null && (
                          <span className="num text-fg-3">
                            {" "}
                            (middle half {duration(p.q1)}–{duration(p.q3)})
                          </span>
                        )}
                      </div>
                    </div>
                  }
                  style={{ left: x(p.time!), top: 8 + y(p.rate!) }}
                />
              );
            })}
          </>
        )}
      </div>
      {skipped.length > 0 && (
        <p className="flex flex-wrap items-center gap-1.5 border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
          Not plotted, no known outcome or time:
          {skipped.map((p) => (
            <RunMarker key={p.index} index={p.index} size={15} className="!text-[9.5px]" />
          ))}
        </p>
      )}
    </section>
  );
}

function Families({ runs, state, focus }: { runs: RunView[]; state: CompareState; focus: Focus }) {
  const { hover, setHover } = focus;
  const families = groupCases(state.align.shared);
  return (
    <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Ground Truth by scenario">
      <header className="border-b border-line px-4 py-3">
        <h2 className="text-[13.5px] font-medium">By scenario</h2>
        <p className="mt-0.5 text-[12.5px] text-fg-3">Ground Truth passes per scenario on the {state.align.shared.length} shared cases. Bar height is passed over known.</p>
      </header>
      {families.length === 0 ? (
        <p className="px-4 py-10 text-center text-[13px] text-fg-3">These runs share no cases.</p>
      ) : (
        <div className="overflow-hidden rounded-b-lg">
        <div className="-mr-px -mb-px grid [grid-template-columns:repeat(auto-fill,minmax(176px,1fr))]">
          {families.map((family) => {
            const ids = family.cases.map((c) => c.id);
            return (
              <div key={family.family} className="grid content-start gap-2 border-r border-b border-line px-3.5 py-3">
                <div className="flex min-w-0 items-baseline justify-between gap-2">
                  <FamilyCard family={family.family} ids={ids} side="top">
                    <span tabIndex={0} className={clsx(HINT, "truncate text-[12.5px] text-fg-2 hover:text-fg")}>
                      {humanize(family.family)}
                    </span>
                  </FamilyCard>
                  <span className="num shrink-0 text-[11px] text-fg-3">{ids.length}</span>
                </div>
                <div className="flex h-[72px] items-end gap-1" onMouseLeave={() => setHover(null)}>
                  {runs.map((view, index) => {
                    const states = ids.map((id) => stateOf(view.run, id));
                    const known = states.filter((s) => s === "pass" || s === "fail").length;
                    const passed = states.filter((s) => s === "pass").length;
                    const share = known ? passed / known : null;
                    const dim = hover !== null && hover !== index;
                    return (
                      <div
                        key={view.ref}
                        onMouseEnter={() => setHover(index)}
                        className={clsx("flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1 transition-opacity", dim && "opacity-30")}
                        title={`Run ${index + 1}: ${known ? `${passed} of ${known} known passed` : "no known outcome"}`}
                      >
                        <span className="num text-[10.5px] leading-none text-fg-2">{known ? `${passed}/${known}` : "—"}</span>
                        <span className="relative w-full max-w-[22px] flex-1 overflow-hidden rounded-[2px] bg-track">
                          {share === null ? (
                            <span className="hatch absolute inset-0" />
                          ) : (
                            <span className={clsx("absolute inset-x-0 bottom-0", index === 0 ? "bg-accent" : "bg-fg-3")} style={{ height: `${Math.max(share * 100, 3)}%` }} />
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-1">
                  {runs.map((view, index) => (
                    <span key={view.ref} className="flex min-w-0 flex-1 justify-center">
                      <RunMarker index={index} size={15} className="!text-[9.5px]" />
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        </div>
      )}
    </section>
  );
}

export default function Visual() {
  const state = useCompare();
  const [hovered, setHover] = useState<Hover>(null);
  const [pinned, pin] = useState<Hover>(null);
  const hover = hovered ?? pinned;
  const focus: Focus = { hover, setHover, pinned, pin };
  if (state.isLoading) return <CompareLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (state.runs.length < 2) return <ErrorState error={new Error("At least two recorded runs are needed to compare.")} />;

  const { runs } = state;
  const stats = runs.map((view) => sideStats(view.run, state.casesFor(view)));

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px] xl:items-start">
      <aside className="grid gap-4 xl:order-2">
        <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Runs in this comparison">
          <header className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
            <h2 className="text-[13.5px] font-medium">{runs.length} runs</h2>
            <RunPicker state={state} />
          </header>
          <ul className="grid gap-px bg-line sm:grid-cols-2 xl:grid-cols-1">
            {runs.map((view, index) => (
              <li
                key={view.ref}
                onMouseEnter={() => setHover(index)}
                onMouseLeave={() => setHover(null)}
                className={clsx("bg-surface px-3 py-2.5 transition-colors", hover === index && "bg-surface-2")}
              >
                <RunHead view={view} index={index} state={state} />
              </li>
            ))}
          </ul>
          <div className="border-t border-line px-4 py-3">
            <ScopeToggle state={state} />
          </div>
        </section>
        <CompareNotice state={state} />
        <AlignmentPanel state={state} compact />
      </aside>
      <div className="grid min-w-0 gap-4 xl:order-1">
        {pinned !== null && (
          <p className="flex flex-wrap items-center gap-2 text-[12.5px] text-fg-2">
            Following <RunMarker index={pinned} /> <span className="ident">{runs[pinned]?.debug}</span>
            <button type="button" onClick={() => pin(null)} className="h-7 cursor-pointer rounded-md px-2 text-fg-3 hover:bg-surface-2 hover:text-fg">
              Release
            </button>
          </p>
        )}
        <MetricStrips runs={runs} stats={stats} focus={focus} />
        <Scatter runs={runs} stats={stats} state={state} focus={focus} />
        <Families runs={runs} state={state} focus={focus} />
      </div>
    </div>
  );
}
