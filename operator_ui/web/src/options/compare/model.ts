// Pure comparison logic shared by the Runs and Compare options. It mirrors
// POST /api/compare in operator_ui/app.py (shared cases are the intersection
// of each run's planned case set; 2–8 distinct runs) and adds the per-case
// Ground Truth diff the options need. Nothing here infers a missing outcome.
import { median } from "d3-array";
import type { CaseRow, RunWithCases } from "@/api/types";
import { modelInfo } from "@/data/models";
import { caseOutcome, techniqueLabel } from "@/lib/explore";

/** Returned verbatim by the backend's /api/compare. */
export const CAUTION = "Descriptive comparison. Check case, repetition, provider, API model, and Verification model alignment before attributing a difference.";

export const MIN_COMPARE = 2;
export const MAX_COMPARE = 8;

export type CaseState = "pass" | "fail" | "unknown" | "absent";

export const joinModels = (values: string[]) => (values.length ? values.join(" + ") : "unrecorded");
export const debugOf = (run: RunWithCases) => joinModels(run.models.DebugAgent);

// Run exports do not record where the debug model was served; the model
// reference facts do. Kept coarse on purpose.
export function providerOf(run: RunWithCases): string {
  const debug = run.models.DebugAgent[0];
  const served = debug ? modelInfo(debug)?.served : undefined;
  if (!served) return "unrecorded";
  if (/openai api/i.test(served)) return "OpenAI API";
  if (/ollama/i.test(served)) return "Ollama";
  return served;
}

const rowCache = new WeakMap<RunWithCases, Map<string, CaseRow>>();
export function rowsOf(run: RunWithCases): Map<string, CaseRow> {
  let rows = rowCache.get(run);
  if (!rows) {
    rows = new Map(run.case_rows.map((row) => [row.case, row]));
    rowCache.set(run, rows);
  }
  return rows;
}

export function stateOf(run: RunWithCases, caseId: string): CaseState {
  const row = rowsOf(run).get(caseId);
  return row ? caseOutcome(row) : "absent";
}

export function rowCost(row: CaseRow): number | null {
  const values = [row.metrics.api?.cost, row.metrics.debug?.cost, row.metrics.verification?.cost].filter((v): v is number => typeof v === "number");
  return values.length ? values.reduce((a, b) => a + b, 0) : null;
}

export function rowTokens(row: CaseRow): number | null {
  const values = [row.metrics.api?.total_tokens, row.metrics.debug?.total_tokens, row.metrics.verification?.total_tokens].filter((v): v is number => typeof v === "number");
  return values.length ? values.reduce((a, b) => a + b, 0) : null;
}

export interface Dimension {
  key: "cases" | "repetition" | "provider" | "api" | "verifier" | "technique" | "source" | "debug";
  label: string;
  /** One value per run, in comparison order. */
  values: string[];
  same: boolean;
  /** Informational rows never make a comparison "not aligned". */
  info?: boolean;
  note?: string;
}

export interface Repetition {
  index: number;
  of: number;
  min: number | null;
  max: number | null;
}

export interface Alignment {
  shared: string[];
  union: string[];
  alignedCases: boolean;
  dimensions: Dimension[];
  aligned: boolean;
  /** Labels of the critical dimensions that differ. */
  differs: string[];
}

const allSame = (values: string[]) => values.every((value) => value === values[0]);

export function sharedCases(runs: RunWithCases[]): string[] {
  if (!runs.length) return [];
  const [first, ...rest] = runs.map((run) => new Set(run.cases));
  return [...first].filter((id) => rest.every((set) => set.has(id))).sort();
}

export function alignment(runs: RunWithCases[], repetitions?: (Repetition | undefined)[]): Alignment {
  const shared = sharedCases(runs);
  const union = [...new Set(runs.flatMap((run) => run.cases))].sort();
  const sets = runs.map((run) => [...run.cases].sort().join(","));
  const alignedCases = allSame(sets);

  const dims: Dimension[] = [
    {
      key: "cases",
      label: "Cases",
      values: runs.map((run) => `${run.cases.length} planned${run.observed_cases < run.planned_cases ? `, ${run.observed_cases} recorded` : ""}`),
      same: alignedCases,
      note: alignedCases ? `Identical case sets` : `${shared.length} shared of ${union.length}`,
    },
  ];
  if (repetitions) {
    const spread = repetitions.filter((r): r is Repetition => !!r && r.of > 1 && r.min !== null && r.max !== null);
    dims.push({
      key: "repetition",
      label: "Repetition",
      values: repetitions.map((r) => (r ? `run ${r.index} of ${r.of}` : "—")),
      same: true,
      info: true,
      note: spread.length
        ? `Each side is one run. Repeated runs of these configurations ranged ${spread.map((r) => `${Math.round((r.min as number) * 100)}–${Math.round((r.max as number) * 100)}%`).join(", ")}.`
        : "Each side is one run with no repetitions to show its spread.",
    });
  }
  const push = (key: Dimension["key"], label: string, values: string[], extra?: Partial<Dimension>) => dims.push({ key, label, values, same: allSame(values), ...extra });
  push("provider", "Provider", runs.map(providerOf), { note: "From model reference facts; run exports do not record it." });
  push("api", "Knowledge model", runs.map((run) => joinModels(run.models.API)));
  push("verifier", "Verification model", runs.map((run) => joinModels(run.models.Verification)));
  push("technique", "Technique", runs.map((run) => techniqueLabel(run.technique)));
  push("source", "Source", runs.map((run) => run.source), { info: true });
  push("debug", "Debug model", runs.map(debugOf), { info: true, note: "Usually the variable under comparison." });

  const differs = dims.filter((d) => !d.info && !d.same).map((d) => d.label);
  return { shared, union, alignedCases, dimensions: dims, aligned: differs.length === 0, differs };
}

export interface SideStats {
  scope: number;
  attempts: number;
  absent: number;
  known: number;
  passed: number;
  failed: number;
  unknown: number;
  rate: number | null;
  verifyCorrect: number;
  verifyComparable: number;
  verifyRate: number | null;
  medianTime: number | null;
  costPerAttempt: number | null;
  costRows: number;
  tokensPerAttempt: number | null;
  tokenRows: number;
}

/** Metrics over the given cases (null: every recorded case of the run). */
export function sideStats(run: RunWithCases, cases: string[] | null): SideStats {
  const rows = rowsOf(run);
  const ids = cases ?? run.case_rows.map((row) => row.case);
  let attempts = 0;
  let known = 0;
  let passed = 0;
  let verifyCorrect = 0;
  let verifyComparable = 0;
  let cost = 0;
  let costRows = 0;
  let tokens = 0;
  let tokenRows = 0;
  const times: number[] = [];
  for (const id of ids) {
    const row = rows.get(id);
    if (!row) continue;
    attempts += 1;
    const outcome = caseOutcome(row);
    if (outcome !== "unknown") {
      known += 1;
      if (outcome === "pass") passed += 1;
      if (row.verified !== null) {
        verifyComparable += 1;
        if (row.verified === row.ground_truth_passed) verifyCorrect += 1;
      }
    }
    if (typeof row.duration_s === "number") times.push(row.duration_s);
    const c = rowCost(row);
    if (c !== null) {
      cost += c;
      costRows += 1;
    }
    const t = rowTokens(row);
    if (t !== null) {
      tokens += t;
      tokenRows += 1;
    }
  }
  return {
    scope: ids.length,
    attempts,
    absent: ids.length - attempts,
    known,
    passed,
    failed: known - passed,
    unknown: attempts - known,
    rate: known ? passed / known : null,
    verifyCorrect,
    verifyComparable,
    verifyRate: verifyComparable ? verifyCorrect / verifyComparable : null,
    medianTime: median(times) ?? null,
    costPerAttempt: costRows ? cost / costRows : null,
    costRows,
    tokensPerAttempt: tokenRows ? tokens / tokenRows : null,
    tokenRows,
  };
}

export interface CaseDiff {
  improved: string[];
  regressed: string[];
  same: number;
  /** Either side unknown or not recorded: no Ground Truth comparison possible. */
  uncomparable: string[];
}

export function caseDiff(base: RunWithCases, other: RunWithCases, cases: string[]): CaseDiff {
  const result: CaseDiff = { improved: [], regressed: [], same: 0, uncomparable: [] };
  for (const id of cases) {
    const a = stateOf(base, id);
    const b = stateOf(other, id);
    if ((a !== "pass" && a !== "fail") || (b !== "pass" && b !== "fail")) result.uncomparable.push(id);
    else if (a === b) result.same += 1;
    else if (b === "pass") result.improved.push(id);
    else result.regressed.push(id);
  }
  return result;
}
