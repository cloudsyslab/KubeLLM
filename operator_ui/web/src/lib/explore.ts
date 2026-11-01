import { median } from "d3-array";
import type { CaseRow, RunSource, RunWithCases, Technique } from "@/api/types";

export type Scope = "canonical" | "exploratory" | "all";

export interface CaseTally {
  case: string;
  attempts: number;
  known: number;
  passed: number;
  failed: number;
  unknown: number;
  durations: number[];
}

// One configuration = one debug model under one API model, verification model,
// technique, and source. Runs inside a configuration are directly comparable.
export interface ModelConfig {
  key: string;
  slug: string;
  debug: string;
  api: string;
  verification: string;
  technique: Technique | null;
  source: RunSource;
  runs: RunWithCases[];
  cases: string[];
  attempts: number;
  known: number;
  passed: number;
  unknown: number;
  rate: number | null;
  runRates: { ref: string; runId: string; rate: number | null; known: number; passed: number }[];
  verifyAgree: number | null;
  verifyComparable: number;
  medianAttemptS: number | null;
  costPerAttempt: number | null;
  costRuns: number;
  tokensPerAttempt: number | null;
  perCase: Map<string, CaseTally>;
  incompleteRuns: number;
  color: string;
}

const join = (values: string[]) => (values.length ? values.join(" + ") : "unrecorded");

const MODEL_COLORS = 9;

export function modelColor(debug: string, palette: string[]): string {
  const index = palette.indexOf(debug);
  return `var(--model-${((index < 0 ? palette.length : index) % MODEL_COLORS) + 1})`;
}

// Canonical models claim the first identity colors so the headline comparison
// never shows two models in the same color.
function identityOrder(runs: RunWithCases[]): string[] {
  const canonical = [...new Set(runs.filter((run) => run.source === "canonical").flatMap((run) => run.models.DebugAgent))].sort();
  const rest = [...new Set(runs.flatMap((run) => run.models.DebugAgent))].filter((model) => !canonical.includes(model)).sort();
  return [...canonical, ...rest];
}

export function inScope(run: RunWithCases, scope: Scope): boolean {
  return scope === "all" || run.source === scope;
}

function tallyCase(tally: CaseTally, row: CaseRow) {
  tally.attempts += 1;
  if (row.ground_truth_configured === false || row.ground_truth_passed === null) tally.unknown += 1;
  else {
    tally.known += 1;
    if (row.ground_truth_passed) tally.passed += 1;
    else tally.failed += 1;
  }
  if (typeof row.duration_s === "number") tally.durations.push(row.duration_s);
}

export function buildConfigs(runs: RunWithCases[], scope: Scope): ModelConfig[] {
  const palette = identityOrder(runs);
  const groups = new Map<string, RunWithCases[]>();
  for (const run of runs) {
    if (!inScope(run, scope)) continue;
    const key = [join(run.models.DebugAgent), join(run.models.API), join(run.models.Verification), run.technique ?? "unknown", run.source].join("|");
    groups.set(key, [...(groups.get(key) ?? []), run]);
  }

  return [...groups.entries()].map(([key, members]) => {
    const [debug, apiModel, verification, technique, source] = key.split("|");
    const perCase = new Map<string, CaseTally>();
    const durations: number[] = [];
    for (const run of members) {
      for (const row of run.case_rows) {
        const tally = perCase.get(row.case) ?? { case: row.case, attempts: 0, known: 0, passed: 0, failed: 0, unknown: 0, durations: [] };
        tallyCase(tally, row);
        perCase.set(row.case, tally);
        if (typeof row.duration_s === "number") durations.push(row.duration_s);
      }
    }
    const tallies = [...perCase.values()];
    const known = tallies.reduce((sum, t) => sum + t.known, 0);
    const passed = tallies.reduce((sum, t) => sum + t.passed, 0);
    const attempts = tallies.reduce((sum, t) => sum + t.attempts, 0);
    const costed = members.filter((run) => typeof run.total_cost === "number" && run.observed_cases > 0);
    const tokened = members.filter((run) => typeof run.total_tokens === "number" && run.observed_cases > 0);
    const verifyComparable = members.reduce((sum, run) => sum + run.verification_comparable, 0);
    const verifyCorrect = members.reduce((sum, run) => sum + run.verification_correct, 0);
    const slug = encodeURIComponent([debug, technique, source].join("~"));
    return {
      key,
      slug,
      debug,
      api: apiModel,
      verification,
      technique: technique === "unknown" ? null : (technique as Technique),
      source: source as RunSource,
      runs: [...members].sort((a, b) => b.run_id.localeCompare(a.run_id)),
      cases: [...perCase.keys()].sort(),
      attempts,
      known,
      passed,
      unknown: attempts - known,
      rate: known ? passed / known : null,
      runRates: members
        .map((run) => ({ ref: run.ref, runId: run.run_id, rate: run.ground_truth_rate, known: run.ground_truth_known, passed: run.ground_truth_passed }))
        .sort((a, b) => a.runId.localeCompare(b.runId)),
      verifyAgree: verifyComparable ? verifyCorrect / verifyComparable : null,
      verifyComparable,
      medianAttemptS: median(durations) ?? null,
      costPerAttempt: costed.length
        ? costed.reduce((sum, run) => sum + (run.total_cost as number), 0) / costed.reduce((sum, run) => sum + run.observed_cases, 0)
        : null,
      costRuns: costed.length,
      tokensPerAttempt: tokened.length
        ? tokened.reduce((sum, run) => sum + (run.total_tokens as number), 0) / tokened.reduce((sum, run) => sum + run.observed_cases, 0)
        : null,
      perCase,
      incompleteRuns: members.filter((run) => run.status === "incomplete").length,
      color: modelColor(debug, palette),
    };
  });
}

export function rankConfigs(configs: ModelConfig[]): ModelConfig[] {
  return [...configs].sort((a, b) => (b.rate ?? -1) - (a.rate ?? -1) || b.known - a.known || a.debug.localeCompare(b.debug));
}

export function suiteCases(configs: ModelConfig[]): string[] {
  return [...new Set(configs.flatMap((config) => config.cases))].sort();
}

export function findConfig(runs: RunWithCases[], slug: string): ModelConfig | undefined {
  return buildConfigs(runs, "all").find((config) => config.slug === slug || decodeURIComponent(config.slug) === slug);
}

export function techniqueLabel(technique: Technique | null): string {
  switch (technique) {
    case "allStepsAtOnce":
      return "All steps at once";
    case "stepByStep":
      return "Step by step";
    case "singleAgent":
      return "Single agent";
    case "knowledgeAgentOnly":
      return "Knowledge agent only";
    default:
      return "Unrecorded technique";
  }
}

export function caseOutcome(row: CaseRow): "pass" | "fail" | "unknown" {
  if (row.ground_truth_configured === false || row.ground_truth_passed === null) return "unknown";
  return row.ground_truth_passed ? "pass" : "fail";
}
