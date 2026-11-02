import clsx from "clsx";
import { useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router";
import { FamilyCard, VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Segmented, Tip } from "@/components/ui";
import { groupCases, humanize } from "@/lib/cases";
import { compact, count, duration, runDate } from "@/lib/format";
import type { RunView } from "../runs/shared";
import { rowsOf, rowTokens, stateOf, type CaseState } from "./model";
import { RunHead, RunMarker, type CompareState } from "./shared";

// The case diff matrix: every case's Ground Truth outcome (or time, or tokens)
// in each selected run, grouped by scenario, with flips against the base
// marked. The Compare page opens it from the metric rows.

export type CaseFilter = "all" | "differ" | "regressed" | "improved";
type Measure = "outcome" | "time" | "tokens";

export interface CaseLine {
  id: string;
  states: CaseState[];
  differ: boolean;
  improvedIn: number[];
  regressedIn: number[];
  shared: boolean;
}

const WORD: Record<CaseState, string> = { pass: "Pass", fail: "Fail", unknown: "Unknown", absent: "—" };

function absentWord(view: RunView, id: string) {
  return view.run.cases.includes(id) ? "Not recorded" : "Not planned";
}

function Markers({ indexes }: { indexes: number[] }) {
  return (
    <span className="inline-flex gap-0.5">
      {indexes.map((i) => (
        <RunMarker key={i} index={i} size={15} className="!text-[9.5px]" />
      ))}
    </span>
  );
}

function Cell({ view, index, line, measure }: { view: RunView; index: number; line: CaseLine; measure: Measure }) {
  const state = line.states[index];
  const row = rowsOf(view.run).get(line.id);
  const improved = line.improvedIn.includes(index);
  const regressed = line.regressedIn.includes(index);
  const word = state === "absent" ? absentWord(view, line.id) : WORD[state];
  const value = measure === "time" ? duration(row?.duration_s) : measure === "tokens" ? compact(row ? rowTokens(row) : null) : null;
  const label = `${line.id}, run ${index + 1}: ${word}${improved ? ", improved against the base" : regressed ? ", regressed against the base" : ""}${value ? `, ${value}` : ""}`;
  const body = (
    <>
      {(improved || regressed) && (
        <span aria-hidden className={clsx("font-semibold", improved ? "text-good" : "text-bad")}>
          {improved ? "↑" : "↓"}
        </span>
      )}
      {value === null ? (
        <span>{state === "absent" ? "—" : word}</span>
      ) : (
        <span className="grid leading-tight">
          <span className="text-fg">{value}</span>
          <span className="text-[10.5px]">{state === "absent" ? word : WORD[state]}</span>
        </span>
      )}
    </>
  );
  const className = clsx(
    "num flex w-full max-w-[148px] items-center justify-center gap-1 rounded-[4px] px-1.5 text-[12px] transition-[box-shadow] hover:ring-1 hover:ring-fg-3",
    measure === "outcome" ? "h-7" : "h-9",
    state === "pass" && "bg-good-soft/45 text-good",
    state === "fail" && "bg-bad-soft text-bad",
    state === "unknown" && "hatch text-fg-3",
    state === "absent" && "border border-dashed border-line-strong text-fg-3",
    (improved || regressed) && "font-medium ring-1",
    improved && "ring-good/50",
    regressed && "ring-bad/60",
  );
  if (state === "absent") {
    return (
      <span className={className} aria-label={label} title={word}>
        {body}
      </span>
    );
  }
  return (
    <Link to={`/runs/${view.ref}#${line.id}`} aria-label={label} title={`Open this attempt in ${runDate(view.run.run_id)}`} className={className}>
      {body}
    </Link>
  );
}

function ChangeNote({ line }: { line: CaseLine }) {
  if (line.regressedIn.length || line.improvedIn.length) {
    return (
      <span className="grid gap-1 text-[12px]">
        {line.regressedIn.length > 0 && (
          <span className="num inline-flex flex-wrap items-center gap-x-1.5 gap-y-0.5 font-medium text-bad">
            <span className="whitespace-nowrap">↓ Regressed</span> <Markers indexes={line.regressedIn} />
          </span>
        )}
        {line.improvedIn.length > 0 && (
          <span className="num inline-flex flex-wrap items-center gap-x-1.5 gap-y-0.5 font-medium text-good">
            <span className="whitespace-nowrap">↑ Improved</span> <Markers indexes={line.improvedIn} />
          </span>
        )}
      </span>
    );
  }
  const unknown = line.states.filter((s) => s === "unknown" || s === "absent").length;
  if (line.differ) return <span className="text-[12px] text-fg-2">Differs; base not known</span>;
  if (unknown) return <span className="text-[12px] text-warn">{unknown} without outcome</span>;
  return <span className="text-[12px] text-fg-3">Same</span>;
}

/** Every case in the union of the selected runs, with its outcome per run and its flips against the base. */
export function useCaseLines(state: CompareState): CaseLine[] {
  const { runs, align } = state;
  return useMemo<CaseLine[]>(() => {
    if (runs.length < 2) return [];
    const sharedSet = new Set(align.shared);
    return align.union.map((id) => {
      const states = runs.map((v) => stateOf(v.run, id));
      const known = states.filter((s) => s === "pass" || s === "fail");
      const base = states[0];
      const baseKnown = base === "pass" || base === "fail";
      const improvedIn: number[] = [];
      const regressedIn: number[] = [];
      if (baseKnown)
        states.forEach((s, i) => {
          if (i === 0) return;
          if (base === "fail" && s === "pass") improvedIn.push(i);
          if (base === "pass" && s === "fail") regressedIn.push(i);
        });
      return { id, states, differ: new Set(known).size > 1, improvedIn, regressedIn, shared: sharedSet.has(id) };
    });
  }, [runs, align]);
}

export function caseCounts(lines: CaseLine[]) {
  return {
    differ: lines.filter((l) => l.differ).length,
    regressed: lines.filter((l) => l.regressedIn.length).length,
    improved: lines.filter((l) => l.improvedIn.length).length,
  };
}

/** The matrix: case filters, the cell measure, the table, and its legend. The caller supplies the frame. */
export function CaseMatrix({ state, lines, filter, onFilter }: { state: CompareState; lines: CaseLine[]; filter: CaseFilter; onFilter: (filter: CaseFilter) => void }) {
  const [measure, setMeasure] = useState<Measure>("outcome");
  const [unshared, setUnshared] = useState(false);
  const { runs, align } = state;

  const inScope = lines.filter((l) => l.shared || unshared);
  const visible = inScope.filter((l) =>
    filter === "all" ? true : filter === "differ" ? l.differ : filter === "regressed" ? l.regressedIn.length > 0 : l.improvedIn.length > 0,
  );
  const byId = new Map(visible.map((l) => [l.id, l]));
  const families = groupCases(visible.map((l) => l.id));
  const counts = caseCounts(inScope);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2.5 sm:px-4">
        <div className="relative max-w-full overflow-x-auto">
          <Segmented
            label="Show cases"
            value={filter}
            onChange={onFilter}
            options={[
              { value: "all", label: "All" },
              { value: "differ", label: <>Differences <span className="num text-fg-3">{counts.differ}</span></>, hint: "Known outcomes disagree between runs" },
              { value: "regressed", label: <>Regressions <span className="num text-fg-3">{counts.regressed}</span></>, hint: "Passed in the base, failed in another run" },
              { value: "improved", label: <>Improvements <span className="num text-fg-3">{counts.improved}</span></>, hint: "Failed in the base, passed in another run" },
            ]}
          />
        </div>
        <Segmented
          label="Cell value"
          value={measure}
          onChange={setMeasure}
          options={[
            { value: "outcome", label: "Outcome" },
            { value: "time", label: "Time" },
            { value: "tokens", label: "Tokens" },
          ]}
        />
        {!align.alignedCases && (
          <label className="inline-flex h-8 cursor-pointer items-center gap-2 rounded-md px-2 text-[12.5px] text-fg-2 hover:bg-surface-2">
            <input type="checkbox" checked={unshared} onChange={(e) => setUnshared(e.target.checked)} className="size-3.5 accent-accent" />
            Include {align.union.length - align.shared.length} unshared {align.union.length - align.shared.length === 1 ? "case" : "cases"}
          </label>
        )}
        <span className="num ml-auto text-[12.5px] text-fg-3" aria-live="polite">
          {count(visible.length)} of {count(inScope.length)} cases
        </span>
      </div>

      <div className="relative overflow-x-auto">
        <table
          className="w-full min-w-[calc(150px_+_var(--runs)_*_var(--cell)_+_130px)] table-fixed border-separate border-spacing-0 text-[12.5px] sm:min-w-[calc(220px_+_var(--runs)_*_var(--cell)_+_150px)]"
          style={{ "--runs": runs.length, "--cell": measure === "outcome" ? "104px" : "116px" } as CSSProperties}
        >
          <colgroup>
            <col className="w-[150px] sm:w-[220px]" />
            {runs.map((view) => (
              <col key={view.ref} />
            ))}
            <col className="w-[130px] sm:w-[150px]" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col" className="label sticky left-0 z-10 border-b border-line bg-surface px-3 pb-2.5 text-left align-bottom !text-[10.5px] font-medium sm:px-4">
                Case
              </th>
              {runs.map((view, index) => (
                <th key={view.ref} scope="col" className="border-b border-line px-1.5 pt-3 pb-2.5 text-left align-top font-normal">
                  <RunHead view={view} index={index} state={state} compact />
                </th>
              ))}
              <th scope="col" className="label border-b border-line px-3 pb-2.5 text-left align-bottom !text-[10.5px] font-medium">
                Against base
              </th>
            </tr>
          </thead>
          {families.map((family) => {
            const ids = family.cases.map((c) => c.id);
            return (
              <tbody key={family.family}>
                <tr>
                  <th scope="rowgroup" className="sticky left-0 z-10 border-b border-line bg-surface px-3 pt-3 pb-1.5 text-left font-normal sm:px-4">
                    <FamilyCard family={family.family} ids={ids}>
                      <span tabIndex={0} className={clsx(HINT, "text-[12.5px] font-medium text-fg")}>
                        {humanize(family.family)}
                      </span>
                    </FamilyCard>
                  </th>
                  {runs.map((view) => {
                    const known = ids.filter((id) => ["pass", "fail"].includes(stateOf(view.run, id)));
                    const passed = ids.filter((id) => stateOf(view.run, id) === "pass").length;
                    return (
                      <td key={view.ref} className="num border-b border-line px-1.5 pt-3 pb-1.5 text-[11.5px] text-fg-3" title={`${passed} of ${known.length} known passed`}>
                        <span className="block max-w-[148px] text-center">
                          {known.length ? (
                            <>
                              <span className="text-fg-2">{passed}</span>/{known.length}
                            </>
                          ) : (
                            "—"
                          )}
                        </span>
                      </td>
                    );
                  })}
                  <td className="border-b border-line" />
                </tr>
                {family.cases.map((item) => {
                  const line = byId.get(item.id)!;
                  const highlight = line.regressedIn.length > 0;
                  return (
                    <tr key={item.id} className="group/row">
                      <th scope="row" className={clsx("sticky left-0 z-10 bg-surface py-[3px] pr-2 pl-3 text-left font-normal sm:pl-4", highlight && "shadow-[inset_2px_0_0_var(--bad)]")}>
                        <span className="flex min-w-0 items-center gap-2">
                          <VariantCard id={item.id}>
                            <span tabIndex={0} className={clsx(HINT, "ident truncate text-[12px] text-fg-2 hover:text-fg")}>
                              {item.variant}
                            </span>
                          </VariantCard>
                          {!line.shared && (
                            <Tip content="Not planned in every selected run, so it is outside the shared comparison.">
                              <span tabIndex={0} className="label shrink-0 !text-[9px] !text-warn">
                                Unshared
                              </span>
                            </Tip>
                          )}
                        </span>
                      </th>
                      {runs.map((view, index) => (
                        <td key={view.ref} className="px-1.5 py-[3px]">
                          <Cell view={view} index={index} line={line} measure={measure} />
                        </td>
                      ))}
                      <td className="px-3 py-[3px]">
                        <ChangeNote line={line} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            );
          })}
          <tfoot>
            <tr>
              <th scope="row" className="label sticky left-0 z-10 border-t border-line-strong bg-surface px-3 py-2.5 text-left !text-[10.5px] font-medium sm:px-4">
                Passed, known
              </th>
              {runs.map((view) => {
                const ids = inScope.map((l) => l.id);
                const known = ids.filter((id) => ["pass", "fail"].includes(stateOf(view.run, id))).length;
                const passed = ids.filter((id) => stateOf(view.run, id) === "pass").length;
                return (
                  <td key={view.ref} className="num border-t border-line-strong px-1.5 py-2.5">
                    <span className="block max-w-[148px] text-center">
                      <span className="font-medium text-fg">{passed}</span>
                      <span className="text-fg-3">/{known}</span>
                    </span>
                  </td>
                );
              })}
              <td className="border-t border-line-strong" />
            </tr>
          </tfoot>
        </table>
        {visible.length === 0 && (
          <p className="px-4 py-10 text-center text-[13px] text-fg-3">
            {filter === "regressed" ? "No case regressed against the base." : filter === "improved" ? "No case improved against the base." : "Every run has the same known outcome on these cases."}
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-[3px] bg-good-soft/45" /> Pass
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-[3px] bg-bad-soft" /> Fail
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="hatch h-3 w-5 rounded-[3px] border border-line" /> Unknown
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-[3px] border border-dashed border-line-strong" /> Not recorded or planned
        </span>
        <span className="num">
          <span className="text-good">↑</span> / <span className="text-bad">↓</span> outcome flipped against the base
        </span>
        <span className="sm:ml-auto">Select a cell to open that attempt.</span>
      </div>
    </>
  );
}
