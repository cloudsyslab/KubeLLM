// The Runs table view: one sortable row per run. Filters, sort, and the row
// limit live in RunsBrowser so they survive switching to the timeline.
import clsx from "clsx";
import { ArrowDown, ArrowUp, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Tip } from "@/components/ui";
import { techniqueLabel } from "@/lib/explore";
import { compact, count, duration, pct, runDate, usd } from "@/lib/format";
import { MAX_COMPARE } from "../compare/model";
import { gtTip, IncompleteTag, RateBar, RunModel, SelectBox, SOURCE_LABEL, techniqueShort, type RunSelection, type RunView } from "./shared";

export type SortKey = "date" | "model" | "technique" | "source" | "cases" | "gt" | "unknown" | "verifier" | "duration" | "cost";
export interface SortState {
  key: SortKey;
  dir: "asc" | "desc";
}
export const DEFAULT_SORT: SortState = { key: "date", dir: "desc" };

interface Column {
  key: SortKey;
  label: string;
  align: "left" | "right";
  hint?: string;
  first: "asc" | "desc";
  value: (view: RunView) => number | string | null;
  className?: string;
}

const COLUMNS: Column[] = [
  { key: "date", label: "Run", align: "left", first: "desc", value: (v) => v.run.run_id, className: "min-w-[200px]" },
  { key: "model", label: "Debug model", align: "left", first: "asc", value: (v) => (v.recorded ? v.debug : null), className: "min-w-[180px]" },
  { key: "technique", label: "Technique", align: "left", first: "asc", value: (v) => v.run.technique },
  { key: "source", label: "Source", align: "left", first: "asc", value: (v) => v.run.source },
  { key: "cases", label: "Cases", align: "right", first: "desc", hint: "Recorded attempts out of planned cases. One attempt per case per run.", value: (v) => v.run.observed_cases },
  {
    key: "gt",
    label: "Ground Truth",
    align: "left",
    first: "desc",
    hint: "Share of attempts with a known Ground Truth outcome that passed. Unknown outcomes are excluded and counted in their own column.",
    value: (v) => v.run.ground_truth_rate,
    className: "min-w-[196px]",
  },
  { key: "unknown", label: "Unknown", align: "right", first: "desc", hint: "Recorded attempts without a Ground Truth outcome. Never counted as passes or failures.", value: (v) => v.run.ground_truth_unavailable },
  {
    key: "verifier",
    label: "Verifier agrees",
    align: "right",
    first: "desc",
    hint: "How often the independent verifier's judgment matched Ground Truth. A separate signal, never proof of success.",
    value: (v) => v.verifierRate,
  },
  { key: "duration", label: "Duration", align: "right", first: "asc", hint: "Recorded wall-clock time of the whole run.", value: (v) => v.run.duration_s },
  { key: "cost", label: "Cost", align: "right", first: "asc", hint: "Recorded API cost of the whole run. A dash means none was recorded; it is not zero.", value: (v) => v.run.total_cost },
];

function compareValues(a: number | string | null, b: number | string | null, dir: "asc" | "desc") {
  // Missing values sort last in either direction.
  if (a === null) return b === null ? 0 : 1;
  if (b === null) return -1;
  const order = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
  return dir === "asc" ? order : -order;
}

export function sortRuns(views: RunView[], sort: SortState): RunView[] {
  const column = COLUMNS.find((c) => c.key === sort.key)!;
  return [...views].sort((a, b) => compareValues(column.value(a), column.value(b), sort.dir) || b.run.run_id.localeCompare(a.run.run_id));
}

/** Clicking the sorted column flips it; another column starts in its natural direction. */
export function nextSort(current: SortState, key: SortKey): SortState {
  const column = COLUMNS.find((c) => c.key === key)!;
  return current.key === key ? { key, dir: current.dir === "asc" ? "desc" : "asc" } : { key, dir: column.first };
}

function HeaderCell({ column, sort, onSort }: { column: Column; sort: SortState; onSort: (key: SortKey) => void }) {
  const sorted = sort.key === column.key;
  const button = (
    <button
      type="button"
      onClick={() => onSort(column.key)}
      className={clsx("inline-flex cursor-pointer items-center gap-1 whitespace-nowrap hover:text-fg", sorted && "text-fg", column.align === "right" && "flex-row-reverse")}
    >
      <span>{column.label}</span>
      {sorted ? sort.dir === "asc" ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" /> : <span className="size-3" />}
    </button>
  );
  return (
    <th
      scope="col"
      aria-sort={sorted ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
      className={clsx("label h-10 border-b border-line px-3 !text-[10.5px] font-medium", column.align === "right" ? "text-right" : "text-left", column.className)}
    >
      {column.hint ? <Tip content={column.hint}>{button}</Tip> : button}
    </th>
  );
}

export function RunsSummary({ views, total }: { views: RunView[]; total?: number }) {
  const attempts = views.reduce((sum, v) => sum + v.run.observed_cases, 0);
  const known = views.reduce((sum, v) => sum + v.run.ground_truth_known, 0);
  const passed = views.reduce((sum, v) => sum + v.run.ground_truth_passed, 0);
  const incomplete = views.filter((v) => v.run.status === "incomplete").length;
  const costed = views.filter((v) => typeof v.run.total_cost === "number").length;
  const items: [string, ReactNode][] = [
    ["Runs", total !== undefined && total !== views.length ? <>{count(views.length)} <span className="text-[12px] font-normal text-fg-3">of {count(total)}</span></> : count(views.length)],
    ["Attempts", count(attempts)],
    ["Ground Truth", <>{pct(known ? passed / known : null)} <span className="text-[12px] font-normal text-fg-3">pooled</span></>],
    ["Known outcomes", <>{count(known)} <span className="text-[12px] font-normal text-fg-3">of {count(attempts)}</span></>],
    ["Incomplete", <span className={incomplete ? "text-warn" : undefined}>{count(incomplete)}</span>],
    ["Cost recorded", <>{count(costed)} <span className="text-[12px] font-normal text-fg-3">of {count(views.length)} runs</span></>],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:flex sm:flex-wrap">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="label !text-[10px]">{label}</dt>
          <dd className="num mt-1 text-[15px] font-medium tracking-[-0.01em]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * The table and its footer, for the rows the browser has already filtered.
 * Rendered inside RunsBrowser's card, under the shared toolbar.
 */
export function RunsTable({
  rows,
  selection,
  sort,
  onSort,
  limit,
  onShowAll,
  onClearFilters,
}: {
  rows: RunView[];
  selection: RunSelection;
  sort: SortState;
  onSort: (key: SortKey) => void;
  limit: number;
  onShowAll: () => void;
  onClearFilters: () => void;
}) {
  const shown = rows.slice(0, limit);
  return (
    <>
      <div className="relative overflow-x-auto">
        <table className="w-full min-w-[1120px] border-collapse text-[13px]">
          <thead>
            <tr>
              <th scope="col" className="h-10 w-10 border-b border-line pl-4 text-left">
                <span className="sr-only">Select for comparison</span>
              </th>
              {COLUMNS.map((column) => (
                <HeaderCell key={column.key} column={column} sort={sort} onSort={onSort} />
              ))}
              <th scope="col" className="w-10 border-b border-line">
                <span className="sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {shown.map((view) => {
              const { run } = view;
              const on = selection.has(view.ref);
              return (
                <tr key={view.ref} className={clsx("group border-b border-line transition-colors last:border-b-0", on ? "bg-accent-soft" : "hover:bg-surface-2/60")}>
                  <td className="pl-4">
                    <SelectBox checked={on} disabled={selection.full} onChange={() => selection.toggle(view.ref)} label={`Select run ${run.run_id} of ${view.debug} for comparison`} />
                  </td>
                  <td className="py-2 pr-3 pl-3">
                    <div className="flex items-center gap-2 whitespace-nowrap">
                      <Link to={`/runs/${view.ref}`} className="text-fg hover:underline hover:decoration-line-strong hover:underline-offset-2">
                        {runDate(run.run_id)}
                      </Link>
                      {run.status === "incomplete" && <IncompleteTag run={run} />}
                    </div>
                    <div className="ident mt-0.5 text-[11px] whitespace-nowrap text-fg-3">{run.run_id}</div>
                  </td>
                  <td className="max-w-[220px] px-3">
                    <RunModel view={view} />
                  </td>
                  <td className="px-3 whitespace-nowrap text-fg-2" title={techniqueLabel(run.technique)}>
                    {techniqueShort(run.technique)}
                  </td>
                  <td className={clsx("px-3", run.source === "canonical" ? "text-fg-2" : "text-fg-3")}>{SOURCE_LABEL[run.source]}</td>
                  <td className="num px-3 text-right whitespace-nowrap">
                    {view.missing > 0 ? (
                      <Tip content={`${view.missing} planned ${view.missing === 1 ? "case has" : "cases have"} no recorded attempt.`}>
                        <span className="text-warn">{run.observed_cases}</span>
                      </Tip>
                    ) : (
                      <span className="text-fg-2">{run.observed_cases}</span>
                    )}
                    <span className="text-fg-3">/{run.planned_cases}</span>
                  </td>
                  <td className="px-3">
                    <Tip content={gtTip(run)}>
                      <span className="inline-flex items-center gap-2.5">
                        <RateBar rate={run.ground_truth_rate} width={64} active={on} />
                        <span className="num w-[46px] text-right font-medium">{pct(run.ground_truth_rate)}</span>
                        <span className="num w-[40px] text-[11.5px] text-fg-3">
                          {run.ground_truth_passed}/{run.ground_truth_known}
                        </span>
                      </span>
                    </Tip>
                  </td>
                  <td className={clsx("num px-3 text-right", run.ground_truth_unavailable ? "text-warn" : "text-fg-3")}>{run.ground_truth_unavailable}</td>
                  <td className="num px-3 text-right text-fg-2">
                    {view.verifierRate === null ? (
                      <span className="text-fg-3" title="No attempt had both a verifier judgment and a known Ground Truth outcome.">
                        —
                      </span>
                    ) : (
                      <span title={`${run.verification_correct} of ${run.verification_comparable} comparable attempts agreed with Ground Truth`}>{pct(view.verifierRate, 0)}</span>
                    )}
                  </td>
                  <td className="num px-3 text-right whitespace-nowrap text-fg-2">{duration(run.duration_s)}</td>
                  <td className="num px-3 text-right text-fg-2" title={typeof run.total_tokens === "number" ? `${compact(run.total_tokens)} tokens` : undefined}>
                    {usd(run.total_cost)}
                  </td>
                  <td className="pr-3 text-right">
                    <Link to={`/runs/${view.ref}`} aria-label={`Open run ${run.run_id}`} className="inline-grid size-6 place-items-center rounded text-fg-3 group-hover:text-fg">
                      <ChevronRight className="size-4" strokeWidth={1.75} />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && (
          <div className="px-4 py-12 text-center text-[13px] text-fg-3">
            No recorded run matches these filters.{" "}
            <button type="button" onClick={onClearFilters} className="cursor-pointer text-fg-2 underline decoration-line-strong underline-offset-2 hover:text-fg">
              Clear filters
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
        {rows.length > limit ? (
          <button type="button" onClick={onShowAll} className="cursor-pointer text-fg-2 hover:text-fg">
            Show all {count(rows.length)} runs
          </button>
        ) : (
          <span>
            Showing {count(rows.length)} {rows.length === 1 ? "run" : "runs"}
          </span>
        )}
        <span className="sm:ml-auto">
          {selection.selected.length === 0 ? `Tick 2–${MAX_COMPARE} runs to compare them. ` : ""}Rates exclude unknown outcomes; a dash means not recorded.
        </span>
      </div>
    </>
  );
}
