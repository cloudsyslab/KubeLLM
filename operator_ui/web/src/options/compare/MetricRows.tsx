import clsx from "clsx";
import { ArrowDown, ArrowUp, ArrowUpRight, ChevronDown } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { Link } from "react-router";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Tip } from "@/components/ui";
import { caseFamily, humanize } from "@/lib/cases";
import { compact, duration, pct, runDate, usd } from "@/lib/format";
import { RateBar, RunModel, type RunView } from "../runs/shared";
import type { CaseDiff, SideStats } from "./model";
import { FlipCounts, NeutralDelta, OutcomeDelta, RunHead, RunMarker, type Better, type CompareState } from "./shared";

// The metric rows: one run is the base; each row shows every run's value, its
// delta, and for Ground Truth how many shared cases flipped. FlipLists names
// the flipped cases per run.

interface Cell {
  value: ReactNode;
  sub?: ReactNode;
  delta?: ReactNode;
  extra?: ReactNode;
}

interface MetricRow {
  key: string;
  label: string;
  hint: string;
  better?: Better;
  cell: (stats: SideStats, view: RunView, index: number) => Cell;
}

function rows(base: SideStats, baseView: RunView, diffs: (CaseDiff | null)[], onSeeCases?: () => void): MetricRow[] {
  return [
    {
      key: "gt",
      label: "Ground Truth success",
      hint: "Share of attempts with a known Ground Truth outcome that passed. Unknown outcomes are excluded. Improved and regressed count shared cases whose outcome flipped against the base.",
      better: "higher",
      cell: (s, _v, i) => {
        const diff = diffs[i];
        const flips = diff ? diff.improved.length + diff.regressed.length : 0;
        return {
          value: pct(s.rate),
          sub: `${s.passed} of ${s.known} known`,
          extra: <RateBar rate={s.rate} width={120} active={i === 0} />,
          delta: i === 0 ? undefined : (
            <span className="grid justify-items-start gap-1">
              <OutcomeDelta base={base.rate} value={s.rate} />
              {diff && <FlipCounts improved={diff.improved.length} regressed={diff.regressed.length} uncomparable={diff.uncomparable.length} />}
              {onSeeCases && flips > 0 && (
                <button
                  type="button"
                  onClick={onSeeCases}
                  className="-ml-1 inline-flex h-6 cursor-pointer items-center gap-0.5 rounded-[4px] px-1 text-[12px] text-fg-3 hover:bg-surface-2 hover:text-fg"
                >
                  See which cases <ChevronDown className="size-3" strokeWidth={1.75} />
                </button>
              )}
            </span>
          ),
        };
      },
    },
    {
      key: "unknown",
      label: "Unknown outcomes",
      hint: "Recorded attempts with no Ground Truth outcome, plus cases in scope with no recorded attempt. Neither is counted as a pass or a failure.",
      cell: (s) => ({
        value: <span className={s.unknown ? "text-warn" : undefined}>{s.unknown}</span>,
        sub: (
          <>
            of {s.attempts} recorded
            {s.absent > 0 && <span className="text-warn"> · {s.absent} not recorded</span>}
          </>
        ),
      }),
    },
    {
      key: "verifier",
      label: "Verifier agrees",
      hint: "How often the independent verifier's judgment matched Ground Truth on attempts where both exist. A separate signal, never proof of success.",
      better: "higher",
      cell: (s, _v, i) => ({
        value: pct(s.verifyRate, 0),
        sub: s.verifyComparable ? `${s.verifyCorrect} of ${s.verifyComparable} comparable` : "No comparable attempts",
        extra: <RateBar rate={s.verifyRate} width={120} />,
        delta: i === 0 ? undefined : <NeutralDelta base={base.verifyRate} value={s.verifyRate} better="higher" kind="pp" words={["agrees more", "agrees less"]} />,
      }),
    },
    {
      key: "time",
      label: "Time per attempt",
      hint: "Median wall-clock time of one case attempt, all agent phases included.",
      better: "lower",
      cell: (s, _v, i) => ({
        value: duration(s.medianTime),
        sub: `median of ${s.attempts}`,
        delta: i === 0 ? undefined : <NeutralDelta base={base.medianTime} value={s.medianTime} better="lower" kind="ratio" words={["faster", "slower"]} />,
      }),
    },
    {
      key: "cost",
      label: "Cost per attempt",
      hint: "Recorded API cost across agent roles, averaged over attempts that recorded cost. Missing cost is a dash, never zero.",
      better: "lower",
      cell: (s, _v, i) => ({
        value: usd(s.costPerAttempt),
        sub: s.costRows === s.attempts ? `${s.costRows} attempts` : <span className={s.costRows ? "text-fg-3" : undefined}>{s.costRows} of {s.attempts} recorded cost</span>,
        delta: i === 0 ? undefined : <NeutralDelta base={base.costPerAttempt} value={s.costPerAttempt} better="lower" kind="ratio" words={["cheaper", "costlier"]} />,
      }),
    },
    {
      key: "tokens",
      label: "Tokens per attempt",
      hint: "Recorded tokens across agent roles, averaged over attempts that recorded tokens.",
      better: "lower",
      cell: (s, _v, i) => ({
        value: compact(s.tokensPerAttempt),
        sub: `${s.tokenRows} of ${s.attempts} recorded`,
        delta: i === 0 ? undefined : <NeutralDelta base={base.tokensPerAttempt} value={s.tokensPerAttempt} better="lower" kind="ratio" words={["fewer", "more"]} />,
      }),
    },
    {
      key: "run",
      label: "Whole run, as recorded",
      hint: "The run's own summary: total duration and cost over every case it ran, independent of the case scope above.",
      cell: (_s, v, i) => ({
        value: duration(v.run.duration_s),
        sub: (
          <>
            {usd(v.run.total_cost)} · {v.run.observed_cases}/{v.run.planned_cases} cases
          </>
        ),
        delta: i === 0 ? undefined : <NeutralDelta base={baseView.run.duration_s} value={v.run.duration_s} better="lower" kind="ratio" words={["shorter", "longer"]} />,
      }),
    },
  ];
}

function MetricLabel({ row }: { row: MetricRow }) {
  return (
    <div className="grid gap-0.5">
      <Tip content={row.hint}>
        <span tabIndex={0} className={clsx(HINT, "w-fit text-[13px] font-medium text-fg")}>
          {row.label}
        </span>
      </Tip>
      {row.better && (
        <span className="inline-flex items-center gap-1 text-[11.5px] text-fg-3">
          {row.better === "higher" ? <ArrowUp className="size-3" strokeWidth={2} /> : <ArrowDown className="size-3" strokeWidth={2} />}
          {row.better === "higher" ? "Higher is better" : "Lower is better"}
        </span>
      )}
    </div>
  );
}

function ChangeList({ ids, view, kind }: { ids: string[]; view: RunView; kind: "improved" | "regressed" }) {
  if (!ids.length) return <p className="text-[12.5px] text-fg-3">None</p>;
  return (
    <ul className="grid gap-1">
      {ids.map((id) => {
        const { family, variant } = caseFamily(id);
        return (
          <li key={id} className="flex items-center gap-2 text-[12.5px]">
            <span aria-hidden className={clsx("num w-3 shrink-0 font-medium", kind === "improved" ? "text-good" : "text-bad")}>
              {kind === "improved" ? "↑" : "↓"}
            </span>
            <VariantCard id={id} side="top">
              <span tabIndex={0} className={clsx(HINT, "min-w-0 truncate text-fg-2")}>
                {humanize(family)} <span className="ident text-fg-3">· {variant}</span>
              </span>
            </VariantCard>
            <Link to={`/runs/${view.ref}#${id}`} className="ml-auto inline-flex shrink-0 items-center gap-0.5 text-[12px] text-fg-3 hover:text-fg" aria-label={`Open the ${id} attempt in this run`}>
              Attempt <ArrowUpRight className="size-3" strokeWidth={1.75} />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

/** Each other run's Ground Truth flips against the base, case by case. The caller supplies the frame. */
export function FlipLists({ state, diffs }: { state: CompareState; diffs: (CaseDiff | null)[] }) {
  const others = state.runs.slice(1);
  return (
    <div className="divide-y divide-line">
      {others.map((view, k) => {
        const index = k + 1;
        const diff = diffs[index]!;
        const changed = diff.improved.length + diff.regressed.length;
        return (
          <div key={view.ref} className="grid gap-3 px-4 py-3.5 lg:grid-cols-[260px_minmax(0,1fr)]">
            <div className="grid content-start gap-1.5">
              <span className="flex min-w-0 items-center gap-2">
                <RunMarker index={index} />
                <RunModel view={view} className="text-[12.5px] font-medium" />
              </span>
              <span className="pl-[26px] text-[12px] text-fg-3">{runDate(view.run.run_id)}</span>
              <span className="pl-[26px]">
                <FlipCounts improved={diff.improved.length} regressed={diff.regressed.length} uncomparable={diff.uncomparable.length} />
              </span>
            </div>
            {changed === 0 ? (
              <p className="self-center text-[12.5px] text-fg-3">
                Same Ground Truth outcome as the base on all {diff.same} comparable shared cases.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="grid content-start gap-1.5">
                  <div className="label !text-[10px]">Improved · failed in base, passed here</div>
                  <ChangeList ids={diff.improved} view={view} kind="improved" />
                </div>
                <div className="grid content-start gap-1.5">
                  <div className="label !text-[10px]">Regressed · passed in base, failed here</div>
                  <ChangeList ids={diff.regressed} view={view} kind="regressed" />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** The metric rows table. `onSeeCases` adds a path from the Ground Truth flips into the case matrix. */
export function MetricTable({
  state,
  stats,
  diffs,
  onSeeCases,
}: {
  state: CompareState;
  stats: SideStats[];
  diffs: (CaseDiff | null)[];
  onSeeCases?: () => void;
}) {
  const { runs } = state;
  const table = rows(stats[0], runs[0], diffs, onSeeCases);

  return (
    <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Metrics by run">
      <div className="relative overflow-x-auto">
        <table
          className="w-full min-w-[calc(136px_+_var(--runs)_*_176px)] table-fixed border-collapse text-[13px] sm:min-w-[calc(200px_+_var(--runs)_*_196px)]"
          style={{ "--runs": runs.length } as CSSProperties}
        >
          <colgroup>
            <col className="w-[136px] sm:w-[200px]" />
            {runs.map((view) => (
              <col key={view.ref} />
            ))}
          </colgroup>
          <thead>
            <tr>
              <th scope="col" className="label sticky left-0 z-10 border-b border-line bg-surface px-3 py-3 text-left align-bottom !text-[10.5px] font-medium sm:px-4">
                {state.scope === "shared" ? `${state.align.shared.length} shared cases` : "Each run's recorded cases"}
              </th>
              {runs.map((view, index) => (
                <th key={view.ref} scope="col" className={clsx("border-b border-l border-line px-3 py-3 text-left align-top font-normal", index === 0 && "bg-accent-soft/50")}>
                  <RunHead view={view} index={index} state={state} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.map((row) => (
              <tr key={row.key} className={clsx("border-b border-line last:border-b-0", row.key === "run" && "border-t border-t-line-strong")}>
                <th scope="row" className="sticky left-0 z-10 bg-surface px-3 py-3 text-left align-top font-normal sm:px-4">
                  <MetricLabel row={row} />
                </th>
                {runs.map((view, index) => {
                  const cell = row.cell(stats[index], view, index);
                  return (
                    <td key={view.ref} className={clsx("border-l border-line px-3 py-3 align-top", index === 0 && "bg-accent-soft/50")}>
                      <div className="num text-[15px] leading-tight font-medium tracking-[-0.01em] text-fg">{cell.value}</div>
                      {cell.sub && <div className="num mt-0.5 text-[11.5px] text-fg-3">{cell.sub}</div>}
                      {cell.extra && <div className="mt-2">{cell.extra}</div>}
                      {cell.delta && <div className="mt-2 text-[12px]">{cell.delta}</div>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
        Green and red mark Ground Truth outcome changes only. Other deltas are descriptive: an arrow, the size of the change, and its direction in words.
      </p>
    </section>
  );
}
