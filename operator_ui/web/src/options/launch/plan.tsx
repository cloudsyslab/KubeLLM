import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { median } from "d3-array";
import { ArrowUpRight, ChevronDown, Minus, Plus, Search, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { api } from "@/api/client";
import type { RunWithCases, Technique } from "@/api/types";
import { FamilyCard, VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { displayModel } from "@/components/charts";
import { LabLogo, ModelCard } from "@/components/ModelCard";
import { Button, Tip } from "@/components/ui";
import data from "@/data/cases.json";
import { labOf, modelInfo } from "@/data/models";
import { caseFamily, groupCases, humanize } from "@/lib/cases";
import { buildConfigs, techniqueLabel, type ModelConfig } from "@/lib/explore";
import { count, duration, pct, usd } from "@/lib/format";
import { FreshnessBar, LANE, READINESS_TTL_MIN, StatusWord, countdown, freshnessLine, readiness, useFreshness, type Freshness } from "../environment/readiness";

// The campaign request and its limits, mirrored from operator_ui/config.py
// validate_campaign; attempt order and labels from worker._campaign_items.

export const MAX_ATTEMPTS = 5000;
export const MAX_MODELS = 20;
export const MAX_REPETITIONS = 500;
const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,119}$/;

export const CATALOG: string[] = Object.keys((data as unknown as { cases: Record<string, unknown> }).cases).sort();
export const FAMILIES = groupCases(CATALOG);
export const BASE_CASES = CATALOG.filter((id) => caseFamily(id).variant === "base");

export const TECHNIQUES: { id: Technique; blurb: string }[] = [
  { id: "allStepsAtOnce", blurb: "Knowledge guidance goes to a generative tools agent that diagnoses and acts; Verification and Ground Truth follow." },
  { id: "stepByStep", blurb: "The tools agent runs the knowledge guidance one numbered step at a time." },
  { id: "singleAgent", blurb: "One generative agent diagnoses and acts. Verification is omitted by design." },
  { id: "knowledgeAgentOnly", blurb: "The Knowledge Agent returns a strict command plan that is validated and executed as is." },
];

export interface Plan {
  cases: string[];
  techniques: Technique[];
  models: string[];
  repetitions: number;
  apiModel: string;
  verificationModel: string;
}

export const EMPTY_PLAN: Plan = { cases: [], techniques: ["allStepsAtOnce"], models: [], repetitions: 1, apiModel: "", verificationModel: "" };

export function validModelId(value: string): boolean {
  const v = value.trim();
  return !v || (MODEL_RE.test(v) && !v.includes("://") && !v.includes("@"));
}

/** The models the worker iterates: none selected means the case default. */
export const effectiveModels = (plan: Plan): (string | null)[] => (plan.models.length ? plan.models : [null]);

export function plannedCount(plan: Plan): number {
  return plan.cases.length * plan.techniques.length * effectiveModels(plan).length * plan.repetitions;
}

/** validate_campaign's messages, in its order. */
export function validate(plan: Plan): string[] {
  const errors: string[] = [];
  if (!plan.cases.length) errors.push("Select at least one available case.");
  if (!plan.techniques.length) errors.push("Select one or more supported execution techniques.");
  if (plan.models.length > MAX_MODELS) errors.push("Choose up to 20 DebugAgent models per campaign.");
  if (plan.models.some((m) => !validModelId(m))) errors.push("A model name contains unsupported characters.");
  if (!Number.isInteger(plan.repetitions) || plan.repetitions < 1 || plan.repetitions > MAX_REPETITIONS) errors.push("Repetitions must be between 1 and 500.");
  if (!validModelId(plan.apiModel)) errors.push("API model contains unsupported characters.");
  if (!validModelId(plan.verificationModel)) errors.push("Verification model contains unsupported characters.");
  if (errors.length === 0 && plannedCount(plan) > MAX_ATTEMPTS) errors.push(`This campaign exceeds the ${count(MAX_ATTEMPTS)} attempt limit.`);
  return errors;
}

/** POST /api/campaign body. */
export function requestBody(plan: Plan) {
  return {
    cases: orderCases(plan.cases),
    techniques: plan.techniques,
    debug_models: plan.models,
    api_model: plan.apiModel.trim(),
    verification_model: plan.verificationModel.trim(),
    repetitions: plan.repetitions,
  };
}

export const orderCases = (cases: string[]) => CATALOG.filter((id) => cases.includes(id));

export interface PlannedAttempt {
  sequence: number;
  case: string;
  model: string | null;
  technique: Technique;
  repetition: number;
}

/** Attempt `index` (0-based) of itertools.product(cases, models, techniques, repetitions). */
export function attemptAt(plan: Plan, index: number): PlannedAttempt {
  const cases = orderCases(plan.cases);
  const models = effectiveModels(plan);
  const r = plan.repetitions;
  const t = plan.techniques.length;
  const m = models.length;
  const rep = index % r;
  const tech = Math.floor(index / r) % t;
  const model = Math.floor(index / (r * t)) % m;
  const c = Math.floor(index / (r * t * m));
  return { sequence: index + 1, case: cases[c], model: models[model], technique: plan.techniques[tech], repetition: rep + 1 };
}

/** current_label, exactly as worker.py writes it. */
export const attemptLabel = (a: PlannedAttempt) => `${a.case} · ${a.technique} · ${a.model ?? "configured case default"} · repetition ${a.repetition}`;

/** The first attempt's runner invocation, with the worker's real flags. Paths shortened. */
export function runnerCommand(plan: Plan): string[] {
  if (!plan.cases.length || !plan.techniques.length) return [];
  const a = attemptAt(plan, 0);
  const lines = [
    "python3 debug_assistant_latest/runner.py",
    `  --lab-config ${LANE.selector}`,
    `  --output-dir .local/operator_ui/jobs/<job>/attempts/0001-${a.case}-${a.technique}-${a.model ? "<model-key>" : "default"}`,
    `  --technique ${a.technique}`,
    `  ${a.case}`,
  ];
  if (a.model) lines.push(`  --debug-model ${a.model}`);
  if (plan.apiModel.trim()) lines.push(`  --api-model ${plan.apiModel.trim()}`);
  if (plan.verificationModel.trim()) lines.push(`  --verification-model ${plan.verificationModel.trim()}`);
  return lines;
}

// ---------------------------------------------------------------- recorded history

export interface CellHistory {
  attempts: number;
  known: number;
  passed: number;
  durations: number[];
}

export interface ModelStats {
  id: string;
  config?: ModelConfig;
  attempts: number;
  runs: number;
  techniques: Set<Technique>;
  /** Headline: the canonical configuration when there is one. */
  rate: number | null;
  rateLabel: string;
  medianS: number | null;
  costPerAttempt: number | null;
  notInstalled: boolean;
}

export interface History {
  models: ModelStats[];
  cell: (model: string, caseId: string, techniques?: Technique[]) => CellHistory;
  combo: (model: string | null, technique: Technique) => { medianS: number | null; cost: number | null; n: number; basis: "recorded" | "model" | "technique" | "none" };
  caseMedian: (model: string | null, technique: Technique, caseId: string) => number | null;
}

const key = (...parts: string[]) => parts.join("|");

function buildHistory(runs: RunWithCases[]): History {
  const cells = new Map<string, CellHistory>();
  const comboDur = new Map<string, number[]>();
  const comboCost = new Map<string, { cost: number; n: number }>();
  const modelDur = new Map<string, number[]>();
  const techDur = new Map<string, number[]>();
  const techCost = new Map<string, { cost: number; n: number }>();
  const modelRuns = new Map<string, number>();

  const push = <T,>(map: Map<string, T[]>, k: string, v: T) => map.set(k, [...(map.get(k) ?? []), v]);
  for (const run of runs) {
    const debug = run.models.DebugAgent[0];
    const technique = run.technique;
    if (!debug || !technique || run.models.DebugAgent.length !== 1) continue;
    modelRuns.set(debug, (modelRuns.get(debug) ?? 0) + 1);
    if (typeof run.total_cost === "number" && run.observed_cases > 0) {
      for (const [map, k] of [[comboCost, key(debug, technique)], [techCost, technique]] as const) {
        const acc = map.get(k) ?? { cost: 0, n: 0 };
        map.set(k, { cost: acc.cost + run.total_cost, n: acc.n + run.observed_cases });
      }
    }
    for (const row of run.case_rows) {
      const k = key(debug, technique, row.case);
      const cell = cells.get(k) ?? { attempts: 0, known: 0, passed: 0, durations: [] };
      cell.attempts += 1;
      if (row.ground_truth_configured !== false && row.ground_truth_passed !== null) {
        cell.known += 1;
        if (row.ground_truth_passed) cell.passed += 1;
      }
      if (typeof row.duration_s === "number" && row.duration_s > 0) {
        cell.durations.push(row.duration_s);
        push(comboDur, key(debug, technique), row.duration_s);
        push(modelDur, debug, row.duration_s);
        push(techDur, technique, row.duration_s);
      }
      cells.set(k, cell);
    }
  }

  const configs = buildConfigs(runs, "all");
  const ids = [...new Set(configs.map((c) => c.debug))].filter((id) => id !== "unrecorded");
  const models: ModelStats[] = ids.map((id) => {
    const own = configs.filter((c) => c.debug === id);
    const canonical = own.find((c) => c.source === "canonical");
    const headline = canonical ?? [...own].sort((a, b) => b.attempts - a.attempts)[0];
    return {
      id,
      config: headline,
      attempts: own.reduce((sum, c) => sum + c.attempts, 0),
      runs: modelRuns.get(id) ?? 0,
      techniques: new Set(own.map((c) => c.technique).filter((t): t is Technique => t !== null)),
      rate: headline?.rate ?? null,
      rateLabel: headline ? `${headline.source === "canonical" ? "Canonical" : "Exploratory"} · ${techniqueLabel(headline.technique).toLowerCase()}` : "",
      medianS: headline?.medianAttemptS ?? null,
      costPerAttempt: headline?.costPerAttempt ?? null,
      notInstalled: modelInfo(id)?.served?.includes("no longer installed") === true,
    };
  });
  // Canonical models first (best recorded rate first), then exploratory-only.
  models.sort((a, b) => Number(b.config?.source === "canonical") - Number(a.config?.source === "canonical") || (b.rate ?? -1) - (a.rate ?? -1) || a.id.localeCompare(b.id));

  const empty: CellHistory = { attempts: 0, known: 0, passed: 0, durations: [] };
  return {
    models,
    cell(model, caseId, techniques) {
      const list = techniques?.length ? techniques : TECHNIQUES.map((t) => t.id);
      const merged: CellHistory = { attempts: 0, known: 0, passed: 0, durations: [] };
      for (const t of list) {
        const c = cells.get(key(model, t, caseId)) ?? empty;
        merged.attempts += c.attempts;
        merged.known += c.known;
        merged.passed += c.passed;
        merged.durations.push(...c.durations);
      }
      return merged;
    },
    combo(model, technique) {
      const exact = model ? comboDur.get(key(model, technique)) : undefined;
      const cost = model ? comboCost.get(key(model, technique)) : undefined;
      if (exact?.length) return { medianS: median(exact) ?? null, cost: cost ? cost.cost / cost.n : null, n: exact.length, basis: "recorded" };
      const byModel = model ? modelDur.get(model) : undefined;
      if (byModel?.length) return { medianS: median(byModel) ?? null, cost: null, n: byModel.length, basis: "model" };
      const byTech = techDur.get(technique);
      const tc = techCost.get(technique);
      if (byTech?.length) return { medianS: median(byTech) ?? null, cost: model ? null : tc ? tc.cost / tc.n : null, n: byTech.length, basis: "technique" };
      return { medianS: null, cost: null, n: 0, basis: "none" };
    },
    caseMedian(model, technique, caseId) {
      if (!model) return null;
      const c = cells.get(key(model, technique, caseId));
      return c?.durations.length ? (median(c.durations) ?? null) : null;
    },
  };
}

export function useHistory(): History | undefined {
  const runs = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  return useMemo(() => (runs.data ? buildHistory(runs.data) : undefined), [runs.data]);
}

export interface Estimate {
  seconds: number | null;
  cost: number | null;
  /** model × technique pairs without their own recorded medians. */
  inferred: number;
  costMissing: number;
  pairs: number;
}

/** Serial runner time and cost from recorded medians; never shown as fact. */
export function estimate(plan: Plan, history: History | undefined): Estimate {
  const pairs = effectiveModels(plan).flatMap((model) => plan.techniques.map((technique) => ({ model, technique })));
  if (!history || !plan.cases.length || !pairs.length) return { seconds: null, cost: null, inferred: 0, costMissing: 0, pairs: pairs.length };
  let seconds = 0;
  let cost = 0;
  let inferred = 0;
  let costMissing = 0;
  let timeMissing = false;
  for (const { model, technique } of pairs) {
    const combo = history.combo(model, technique);
    if (combo.basis !== "recorded") inferred += 1;
    if (combo.medianS === null) timeMissing = true;
    for (const caseId of plan.cases) {
      const s = history.caseMedian(model, technique, caseId) ?? combo.medianS ?? 0;
      seconds += s * plan.repetitions;
    }
    if (combo.cost === null) costMissing += 1;
    else cost += combo.cost * plan.cases.length * plan.repetitions;
  }
  return { seconds: timeMissing ? null : seconds, cost: costMissing === pairs.length ? null : cost, inferred, costMissing, pairs: pairs.length };
}

export function EstimateNote({ est, className }: { est: Estimate; className?: string }) {
  const notes = ["Estimates from recorded medians, serial, excluding queueing."];
  if (est.inferred) notes.push(`${est.inferred} of ${est.pairs} model–technique ${est.pairs === 1 ? "pair has" : "pairs have"} no recorded runs and borrow a broader median.`);
  if (est.costMissing && est.cost !== null) notes.push(`Cost covers ${est.pairs - est.costMissing} of ${est.pairs} pairs.`);
  notes.push("Cost is the recorded run total per attempt (knowledge, debug, and verifier calls); local models add no API cost.");
  return <p className={clsx("text-[11.5px] leading-relaxed text-fg-3", className)}>{notes.join(" ")}</p>;
}

// ---------------------------------------------------------------- small pieces

export function ModelChip({ id, className, size = 13 }: { id: string | null; className?: string; size?: number }) {
  if (!id) return <span className={clsx("text-fg-2", className)}>Case default model</span>;
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-1.5", className)}>
      <LabLogo lab={labOf(id)} size={size} />
      <span className="ident truncate">{displayModel(id)}</span>
    </span>
  );
}

/** Model name with the explorer's model hover card when history exists. */
export function ModelName({ stats, className }: { stats: ModelStats; className?: string }) {
  const chip = <ModelChip id={stats.id} className={className} />;
  if (!stats.config) return chip;
  return (
    <ModelCard config={stats.config} side="right">
      <span tabIndex={0} className={clsx(HINT, "inline-flex min-w-0")}>
        {chip}
      </span>
    </ModelCard>
  );
}

/** A case's variant name ("base", "wrong_name") with its scenario hover card. */
export function CaseName({ id, className, side = "right" }: { id: string; className?: string; side?: "right" | "bottom" | "top" | "left" }) {
  return (
    <VariantCard id={id} side={side}>
      <span tabIndex={0} className={clsx(HINT, "min-w-0 truncate", className)}>
        {caseFamily(id).variant}
      </span>
    </VariantCard>
  );
}

export function FamilyName({ family, ids, className, side = "right" }: { family: string; ids: string[]; className?: string; side?: "right" | "bottom" | "top" | "left" }) {
  return (
    <FamilyCard family={family} ids={ids} side={side}>
      <span tabIndex={0} className={clsx(HINT, "min-w-0 truncate", className)}>
        {humanize(family)}
      </span>
    </FamilyCard>
  );
}

export function Checkbox({ checked, indeterminate, onChange, label, className, disabled }: { checked: boolean; indeterminate?: boolean; onChange: (next: boolean) => void; label: string; className?: string; disabled?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = Boolean(indeterminate) && !checked;
  }, [indeterminate, checked]);
  return (
    <input
      ref={ref}
      type="checkbox"
      aria-label={label}
      checked={checked}
      disabled={disabled}
      onChange={(e) => onChange(e.target.checked)}
      className={clsx("size-3.5 shrink-0 cursor-pointer accent-accent disabled:cursor-not-allowed", className)}
    />
  );
}

const toggle = <T,>(list: T[], value: T, on: boolean) => (on ? (list.includes(value) ? list : [...list, value]) : list.filter((v) => v !== value));
export { toggle };

/** Cases grouped by scenario family, with tri-state family boxes. */
export function CasePicker({ value, onChange, dense, className }: { value: string[]; onChange: (next: string[]) => void; dense?: boolean; className?: string }) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase().replaceAll(" ", "_");
  const families = FAMILIES.map((f) => ({ ...f, cases: f.cases.filter((c) => !q || c.id.includes(q)) })).filter((f) => f.cases.length);
  return (
    <div className={clsx("grid gap-3", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex h-8 min-w-0 flex-1 items-center gap-2 rounded-md border border-line bg-surface px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent sm:max-w-64">
          <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter cases" aria-label="Filter cases" className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
        </label>
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Quick case sets">
          <Button size="sm" variant="ghost" onClick={() => onChange(CATALOG)} aria-pressed={value.length === CATALOG.length}>
            All {CATALOG.length}
          </Button>
          <Tip content="One case per scenario family: the case without a variant suffix. Resource limits has no base case.">
            <Button size="sm" variant="ghost" onClick={() => onChange(BASE_CASES)}>
              Base cases {BASE_CASES.length}
            </Button>
          </Tip>
          <Button size="sm" variant="ghost" onClick={() => onChange([])} disabled={!value.length}>
            Clear
          </Button>
        </div>
      </div>
      <div className={clsx("grid gap-x-6", dense ? "gap-y-2 sm:grid-cols-2 xl:grid-cols-3" : "gap-y-3 sm:grid-cols-2")}>
        {families.map((family) => {
          const ids = family.cases.map((c) => c.id);
          const allIds = FAMILIES.find((f) => f.family === family.family)!.cases.map((c) => c.id);
          const on = ids.filter((id) => value.includes(id)).length;
          return (
            <fieldset key={family.family} className="min-w-0 border-t border-line pt-2">
              <legend className="sr-only">{humanize(family.family)}</legend>
              <div className="flex items-center gap-2 py-0.5">
                <Checkbox
                  label={`All ${humanize(family.family)} cases`}
                  checked={on === ids.length}
                  indeterminate={on > 0}
                  onChange={(next) => onChange(next ? [...new Set([...value, ...ids])] : value.filter((id) => !ids.includes(id)))}
                />
                <FamilyName family={family.family} ids={allIds} className="text-[13px] font-medium text-fg" />
                <span className="num ml-auto text-[11.5px] text-fg-3">
                  {on}/{ids.length}
                </span>
              </div>
              <ul className="mt-0.5 grid gap-0.5 pl-[22px]">
                {family.cases.map((c) => (
                  <li key={c.id} className="flex min-w-0 items-center gap-2 py-0.5 text-[12.5px]">
                    <Checkbox label={c.id} checked={value.includes(c.id)} onChange={(next) => onChange(toggle(value, c.id, next))} />
                    <VariantCard id={c.id} side="right">
                      <span tabIndex={0} className={clsx(HINT, "ident min-w-0 truncate text-fg-2")}>
                        {c.variant === "base" ? "base" : c.variant}
                      </span>
                    </VariantCard>
                  </li>
                ))}
              </ul>
            </fieldset>
          );
        })}
        {!families.length && <p className="text-[12.5px] text-fg-3">No case matches “{query}”.</p>}
      </div>
    </div>
  );
}

export function RepetitionsInput({ value, onChange, className, presets = [1, 3, 5] }: { value: number; onChange: (next: number) => void; className?: string; presets?: number[] }) {
  const clamp = (n: number) => Math.min(MAX_REPETITIONS, Math.max(1, Math.round(n) || 1));
  return (
    <div className={clsx("flex flex-wrap items-center gap-2", className)}>
      <div className="inline-flex h-8 items-center rounded-md border border-line-strong bg-surface">
        <button type="button" aria-label="Fewer repetitions" onClick={() => onChange(clamp(value - 1))} disabled={value <= 1} className="grid h-full w-8 cursor-pointer place-items-center text-fg-2 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40">
          <Minus className="size-3.5" strokeWidth={2} />
        </button>
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={MAX_REPETITIONS}
          value={value}
          aria-label="Repetitions"
          onChange={(e) => onChange(clamp(Number(e.target.value)))}
          className="num h-full w-12 border-x border-line bg-transparent text-center text-[13px] text-fg outline-none [appearance:textfield] focus-visible:bg-surface-2 [&::-webkit-inner-spin-button]:appearance-none"
        />
        <button type="button" aria-label="More repetitions" onClick={() => onChange(clamp(value + 1))} disabled={value >= MAX_REPETITIONS} className="grid h-full w-8 cursor-pointer place-items-center text-fg-2 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40">
          <Plus className="size-3.5" strokeWidth={2} />
        </button>
      </div>
      <div className="flex items-center gap-1" role="group" aria-label="Repetition presets">
        {presets.map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={value === n}
            onClick={() => onChange(n)}
            className={clsx("num h-7 min-w-7 cursor-pointer rounded-md px-2 text-[12.5px]", value === n ? "bg-surface-3 text-fg" : "text-fg-3 hover:bg-surface-2 hover:text-fg")}
          >
            {n}×
          </button>
        ))}
      </div>
    </div>
  );
}

export function FixedModels({ plan, onChange, className }: { plan: Plan; onChange: (next: Partial<Plan>) => void; className?: string }) {
  const field = (id: string, label: string, flag: string, value: string, set: (v: string) => void) => (
    <div className="grid gap-1">
      <label htmlFor={id} className="text-[12.5px] text-fg-2">
        {label} <span className="ident text-fg-3">{flag}</span>
      </label>
      <input
        id={id}
        value={value}
        onChange={(e) => set(e.target.value)}
        placeholder="Case default"
        list="kubellm-fixed-models"
        spellCheck={false}
        aria-invalid={!validModelId(value)}
        className={clsx("ident h-8 rounded-md border bg-surface px-2.5 text-[12.5px] text-fg outline-none placeholder:font-sans placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-accent", validModelId(value) ? "border-line-strong" : "border-warn")}
      />
      {!validModelId(value) && <span className="text-[11.5px] text-warn">Unsupported characters.</span>}
    </div>
  );
  return (
    <div className={clsx("grid gap-3", className)}>
      <datalist id="kubellm-fixed-models">
        <option value="gpt-5-mini" />
        <option value="gpt-5-nano" />
      </datalist>
      <div className="grid gap-3 sm:grid-cols-2">
        {field("api-model", "Knowledge model", "--api-model", plan.apiModel, (v) => onChange({ apiModel: v }))}
        {field("verification-model", "Verifier model", "--verification-model", plan.verificationModel, (v) => onChange({ verificationModel: v }))}
      </div>
      <p className="text-[11.5px] leading-relaxed text-fg-3">
        Blank keeps each case's configured default. Recorded canonical runs used gpt-5-mini for knowledge and gpt-5-nano for verification; changing either makes results not directly comparable with them.
      </p>
    </div>
  );
}

export function NotInstalled({ className, iconOnly }: { className?: string; iconOnly?: boolean }) {
  return (
    <Tip content="models.ts records this model as no longer installed in the lab's Ollama. Preflight checks that required local models are present.">
      <span tabIndex={0} className={clsx("inline-flex items-center gap-1 text-[11.5px] text-warn", className)}>
        <TriangleAlert className="size-3" strokeWidth={2} />
        <span className={clsx(iconOnly && "sr-only")}>Not installed</span>
      </span>
    </Tip>
  );
}

export const formula = (plan: Plan) => {
  const m = effectiveModels(plan).length;
  return [
    `${plan.cases.length} ${plan.cases.length === 1 ? "case" : "cases"}`,
    plan.models.length ? `${m} ${m === 1 ? "model" : "models"}` : "case default model",
    `${plan.techniques.length} ${plan.techniques.length === 1 ? "technique" : "techniques"}`,
    `${plan.repetitions} ${plan.repetitions === 1 ? "repetition" : "repetitions"}`,
  ];
};

// ---------------------------------------------------------------- readiness gate

export function GateSummary({ fresh, compact, className }: { fresh: Freshness; compact?: boolean; className?: string }) {
  return (
    <div className={clsx("grid gap-2", className)}>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <div className="flex items-center gap-2 text-[13px]">
          <StatusWord fresh={fresh} />
          {fresh.state === "checking" && (
            <span className="num text-fg-3">
              {fresh.active.done.length}/{fresh.active.total}
            </span>
          )}
        </div>
        {fresh.state === "fresh" && <span className="num text-[12px] text-fg-3">{countdown(fresh.left)} left</span>}
      </div>
      <FreshnessBar fresh={fresh} />
      {!compact && <p className="text-[12px] leading-snug text-fg-3">{freshnessLine(fresh)}</p>}
    </div>
  );
}

export function PreflightButton({ fresh, size = "sm", variant = "secondary", className }: { fresh: Freshness; size?: "sm" | "md"; variant?: "primary" | "secondary" | "ghost"; className?: string }) {
  const checking = fresh.state === "checking";
  return (
    <Button size={size} variant={variant} className={className} onClick={readiness.run} disabled={checking}>
      {checking ? "Checking…" : fresh.state === "fresh" ? "Run again" : "Run preflight"}
      <span className="font-mono text-[10px] tracking-[0.06em] text-fg-3 uppercase">Demo</span>
    </Button>
  );
}

/** The launch gate: a fresh READY preflight, at most 20 minutes old. */
export function ReadinessGate({ className, compact }: { className?: string; compact?: boolean }) {
  const { fresh } = useFreshness();
  return (
    <div className={clsx("grid gap-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="label">Readiness · {LANE.profile}</span>
        <Link to="/environment" className="inline-flex items-center gap-0.5 text-[12px] text-fg-3 hover:text-fg">
          Environment <ArrowUpRight className="size-3" strokeWidth={1.75} />
        </Link>
      </div>
      <GateSummary fresh={fresh} compact={compact} />
      {fresh.state !== "fresh" && fresh.state !== "checking" && (
        <p className="text-[12px] text-fg-2">Launching needs a ready preflight from the last {READINESS_TTL_MIN} minutes.</p>
      )}
      <PreflightButton fresh={fresh} className="justify-self-start" />
    </div>
  );
}

// ---------------------------------------------------------------- confirmation pieces

/** Planned attempts in run order, paged so large campaigns stay light. */
export function AttemptList({ plan }: { plan: Plan }) {
  const total = plannedCount(plan);
  const [shown, setShown] = useState(60);
  const rows = Array.from({ length: Math.min(shown, total) }, (_, i) => attemptAt(plan, i));
  return (
    <div>
      <ol className="max-h-60 overflow-y-auto rounded-md border border-line bg-bg/40 py-1" aria-label="Planned attempts in run order">
        {rows.map((a) => (
          <li key={a.sequence} className="grid grid-cols-[40px_minmax(0,1fr)] gap-2 px-3 py-[3px] font-mono text-[11.5px] leading-[1.5]">
            <span className="num text-fg-3">{String(a.sequence).padStart(4, "0")}</span>
            <span className="truncate text-fg-2" title={attemptLabel(a)}>
              {attemptLabel(a)}
            </span>
          </li>
        ))}
      </ol>
      {total > shown && (
        <button type="button" onClick={() => setShown((n) => n + 240)} className="mt-1.5 cursor-pointer text-[12px] text-fg-3 hover:text-fg">
          Show {count(Math.min(240, total - shown))} more of {count(total - shown)} remaining
        </button>
      )}
    </div>
  );
}

export function Disclosure({ title, children, defaultOpen }: { title: ReactNode; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(Boolean(defaultOpen));
  return (
    <div className="border-t border-line pt-3">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex w-full cursor-pointer items-center gap-1.5 text-left text-[12.5px] font-medium text-fg-2 hover:text-fg">
        <ChevronDown className={clsx("size-3.5 transition-transform", !open && "-rotate-90")} strokeWidth={2} />
        {title}
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

/** The exact request body and the first runner invocation worker.py would make. */
export function RequestPreview({ plan }: { plan: Plan }) {
  return (
    <>
      <pre className="overflow-x-auto rounded-md bg-surface-2 px-3 py-2.5 font-mono text-[11.5px] leading-[1.6] text-fg-2">{`POST /api/campaign\n${JSON.stringify(requestBody(plan), (k, v) => (k === "cases" && Array.isArray(v) && v.length > 6 ? [...v.slice(0, 6), `… ${v.length - 6} more`] : v), 2)}`}</pre>
      <pre className="mt-2 overflow-x-auto rounded-md bg-surface-2 px-3 py-2.5 font-mono text-[11.5px] leading-[1.6] text-fg-2">{runnerCommand(plan).join(" \\\n")}</pre>
      <p className="mt-1.5 text-[11.5px] text-fg-3">Flags as worker.py passes them; paths shortened.</p>
    </>
  );
}

/** What starting commits the operator to, from worker.py and the job lock. */
export function LaunchNotes({ className }: { className?: string }) {
  return (
    <ul className={clsx("grid gap-1 text-[12px] leading-relaxed text-fg-3", className)}>
      <li>Each attempt runs its case's setup and teardown. Stop takes effect between attempts; completed results are kept.</li>
      <li>The lab runs one operator job at a time; a launch is refused while another job is active.</li>
      <li>Results stay in .local/ until you publish them.</li>
    </ul>
  );
}

export { pct, techniqueLabel };

// ---------------------------------------------------------------- pickers

/** Debug models from recorded runs, with their recorded history. */
export function ModelList({ history, value, onChange, className }: { history: History | undefined; value: string[]; onChange: (next: string[]) => void; className?: string }) {
  const [custom, setCustom] = useState("");
  if (!history) return <div className="h-64 animate-pulse rounded-md bg-surface-2" />;
  const known = new Set(history.models.map((m) => m.id));
  const extra = value.filter((id) => !known.has(id));
  const add = () => {
    const v = custom.trim();
    if (!v || !validModelId(v)) return;
    onChange(toggle(value, v, true));
    setCustom("");
  };
  return (
    <div className={clsx("grid gap-2", className)}>
      <div className="hidden grid-cols-[18px_minmax(0,1fr)_132px_80px_72px] gap-3 px-2 sm:grid">
        <span />
        <span className="label !text-[10px]">Model</span>
        <span className="label !text-[10px]">Recorded GT</span>
        <span className="label !text-[10px]">Median</span>
        <span className="label !text-[10px] text-right">Cost</span>
      </div>
      <ul className="grid">
        {history.models.map((m) => {
          const on = value.includes(m.id);
          const info = modelInfo(m.id);
          return (
            <li key={m.id} className={clsx("border-t border-line first:border-t-0", on && "bg-accent-soft/60")}>
              <label className="grid cursor-pointer grid-cols-[18px_minmax(0,1fr)] items-center gap-x-2.5 gap-y-1 px-2 py-2 sm:grid-cols-[18px_minmax(0,1fr)_132px_80px_72px] sm:gap-x-3">
                <Checkbox label={displayModel(m.id)} checked={on} onChange={(next) => onChange(toggle(value, m.id, next))} />
                <span className="grid min-w-0 gap-0.5">
                  <span className="flex min-w-0 items-center gap-2">
                    <ModelName stats={m} className="text-[13px] text-fg" />
                    {m.notInstalled && <NotInstalled />}
                  </span>
                  <span className="truncate text-[11.5px] text-fg-3">
                    {labOf(m.id)?.name ?? "Lab unconfirmed"}
                    {info?.tier ? ` · ${info.tier}` : ""}
                  </span>
                </span>
                <span className="col-start-2 flex flex-wrap gap-x-3 text-[12px] text-fg-2 sm:contents">
                  <span className="num sm:text-[12.5px]">
                    <Tip content={`${m.rateLabel}: ${m.config?.passed ?? 0} passed of ${m.config?.known ?? 0} known outcomes across ${m.config?.runs.length ?? 0} runs.`}>
                      <span tabIndex={0}>
                        {pct(m.rate)} <span className="text-fg-3">of {m.config?.known ?? 0}</span>
                      </span>
                    </Tip>
                  </span>
                  <span className="num sm:text-[12.5px]">{duration(m.medianS)}</span>
                  <span className="num sm:text-right sm:text-[12.5px]">{usd(m.costPerAttempt)}</span>
                </span>
              </label>
            </li>
          );
        })}
        {extra.map((id) => (
          <li key={id} className="flex items-center gap-2.5 border-t border-line bg-accent-soft/60 px-2 py-2">
            <Checkbox label={id} checked onChange={() => onChange(value.filter((v) => v !== id))} />
            <ModelChip id={id} className="text-[13px] text-fg" />
            <span className="ml-auto text-[11.5px] text-fg-3">No recorded history</span>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-2 border-t border-line px-2 pt-2.5">
        <label htmlFor="custom-model" className="sr-only">
          Other model ID
        </label>
        <input
          id="custom-model"
          value={custom}
          spellCheck={false}
          onChange={(e) => setCustom(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="Other model ID, as the runner accepts it"
          aria-invalid={!validModelId(custom)}
          className={clsx("ident h-8 min-w-0 flex-1 rounded-md border bg-surface px-2.5 text-[12.5px] text-fg outline-none placeholder:font-sans placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-accent", validModelId(custom) ? "border-line" : "border-warn")}
        />
        <Button size="sm" onClick={add} disabled={!custom.trim() || !validModelId(custom)}>
          Add
        </Button>
      </div>
      <p className="px-2 text-[11.5px] text-fg-3">
        Recorded GT: passed over known outcomes in each model's canonical configuration, or its largest exploratory one.{" "}
        {value.length > MAX_MODELS && <span className="text-warn">Up to {MAX_MODELS} models per campaign.</span>}
      </p>
    </div>
  );
}

/** Techniques as selectable cards; shows which selected models have history. */
export function TechniquePicker({ history, plan, onChange, columns = 2 }: { history: History | undefined; plan: Plan; onChange: (next: Technique[]) => void; columns?: 1 | 2 | 4 }) {
  return (
    <div className={clsx("grid gap-2", columns === 2 && "sm:grid-cols-2", columns === 4 && "sm:grid-cols-2 xl:grid-cols-4")} role="group" aria-label="Techniques">
      {TECHNIQUES.map((t) => {
        const on = plan.techniques.includes(t.id);
        const models = effectiveModels(plan).filter((m): m is string => m !== null);
        const covered = history ? models.filter((m) => history.combo(m, t.id).basis === "recorded").length : 0;
        return (
          <label
            key={t.id}
            className={clsx(
              "grid cursor-pointer grid-cols-[18px_minmax(0,1fr)] gap-x-2.5 gap-y-1 rounded-md border px-3 py-2.5 transition-colors",
              on ? "border-accent-line bg-accent-soft" : "border-line hover:border-line-strong",
            )}
          >
            <Checkbox label={techniqueLabel(t.id)} checked={on} onChange={(next) => onChange(toggle(plan.techniques, t.id, next))} className="mt-[3px]" />
            <span className="min-w-0">
              <span className="flex flex-wrap items-baseline gap-x-2">
                <span className="text-[13px] font-medium text-fg">{techniqueLabel(t.id)}</span>
                <span className="ident text-[11px] text-fg-3">{t.id}</span>
              </span>
              <span className="mt-0.5 block text-[12px] leading-snug text-fg-2">{t.blurb}</span>
              {models.length > 0 && (
                <span className={clsx("mt-1 block text-[11.5px]", covered === models.length ? "text-fg-3" : "text-warn")}>
                  {covered === models.length ? "Recorded for every selected model" : `No recorded runs for ${models.length - covered} of ${models.length} selected ${models.length === 1 ? "model" : "models"}`}
                </span>
              )}
            </span>
          </label>
        );
      })}
    </div>
  );
}
