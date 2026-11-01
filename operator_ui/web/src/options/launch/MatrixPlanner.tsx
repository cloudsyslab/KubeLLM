import clsx from "clsx";
import { useRef, useState, type KeyboardEvent } from "react";
import type { Technique } from "@/api/types";
import { caseInfo } from "@/components/CaseCard";
import { displayModel } from "@/components/charts";
import { Button, Tip } from "@/components/ui";
import { DEMO_CASES } from "@/demo/campaign";
import { humanize } from "@/lib/cases";
import { techniqueLabel } from "@/lib/explore";
import { count, duration, usd } from "@/lib/format";
import { LiveAnnouncer, ScenarioSwitch, useFreshness } from "../environment/readiness";
import {
  CATALOG,
  CaseName,
  Checkbox,
  EstimateNote,
  FAMILIES,
  FamilyName,
  GateSummary,
  ModelChip,
  ModelName,
  NotInstalled,
  PreflightButton,
  RepetitionsInput,
  ReviewDialog,
  TECHNIQUES,
  estimate,
  formula,
  plannedCount,
  toggle,
  useHistory,
  validate,
  type CellHistory,
  type Estimate,
  type History,
  type Plan,
} from "./plan";

const ROWS = FAMILIES.flatMap((f) => f.cases.map((c) => c.id));

function HistoryCell({ cell, planned }: { cell: CellHistory; planned: boolean }) {
  const rate = cell.known ? cell.passed / cell.known : null;
  return (
    <span className="grid w-full gap-1 px-1.5">
      <span className={clsx("num text-[11.5px] leading-none", cell.attempts ? (planned ? "text-fg" : "text-fg-2") : "text-fg-3")}>
        {cell.known ? `${cell.passed}/${cell.known}` : cell.attempts ? `${cell.attempts}?` : "—"}
      </span>
      <span aria-hidden className="h-[2px] w-full overflow-hidden rounded-full bg-track">
        {rate !== null && <span className={clsx("block h-full rounded-full", planned ? "bg-fg-3" : "bg-fg-3/45")} style={{ width: `${rate * 100}%` }} />}
      </span>
    </span>
  );
}

type Quick = "gaps" | "mixed" | "failed";
const QUICK: { id: Quick; label: string; hint: string }[] = [
  { id: "gaps", label: "Coverage gaps", hint: "Cases with no recorded attempt for at least one selected model under the selected techniques." },
  { id: "mixed", label: "Mixed history", hint: "Cases where a selected model has both passed and failed Ground Truth before." },
  { id: "failed", label: "Never passed", hint: "Cases where a selected model has known outcomes and passed none of them." },
];

function quickCases(kind: Quick, plan: Plan, history: History): string[] {
  const models = plan.models;
  if (!models.length) return [];
  return CATALOG.filter((caseId) =>
    models.some((m) => {
      const cell = history.cell(m, caseId, plan.techniques);
      if (kind === "gaps") return cell.attempts === 0;
      if (kind === "mixed") return cell.passed > 0 && cell.passed < cell.known;
      return cell.known > 0 && cell.passed === 0;
    }),
  );
}

function Inspector({ focus, plan, history, onPlan }: { focus: { model: string; caseId: string } | null; plan: Plan; history: History; onPlan: (next: Partial<Plan>) => void }) {
  if (!focus) return <p className="text-[12.5px] text-fg-3">Select a cell to see its recorded history by technique.</p>;
  const info = caseInfo(focus.caseId);
  const modelOn = plan.models.includes(focus.model);
  const caseOn = plan.cases.includes(focus.caseId);
  return (
    <div className="grid gap-3">
      <div className="grid gap-1">
        <ModelChip id={focus.model} className="text-[13px] text-fg" />
        <div className="ident text-[12px] text-fg-2">{focus.caseId}</div>
        {info && <p className="text-[12px] leading-relaxed text-fg-3">“{info.symptom.length > 150 ? `${info.symptom.slice(0, 149)}…` : info.symptom}”</p>}
      </div>
      <table className="w-full text-[12px]">
        <caption className="label mb-1 !text-[10px] text-left">Recorded history</caption>
        <tbody>
          {TECHNIQUES.map((t) => {
            const cell = history.cell(focus.model, focus.caseId, [t.id]);
            const med = history.caseMedian(focus.model, t.id, focus.caseId);
            return (
              <tr key={t.id} className={clsx("border-t border-line", !plan.techniques.includes(t.id) && "text-fg-3")}>
                <th scope="row" className="py-1 pr-2 text-left font-normal">
                  {techniqueLabel(t.id)}
                </th>
                <td className="num py-1 text-right">{cell.known ? `${cell.passed}/${cell.known} passed` : cell.attempts ? `${cell.attempts} unknown` : "—"}</td>
                <td className="num py-1 pl-3 text-right text-fg-3">{duration(med)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => onPlan({ models: toggle(plan.models, focus.model, !modelOn) })}>
          {modelOn ? "Remove model" : "Add model"}
        </Button>
        <Button size="sm" onClick={() => onPlan({ cases: toggle(plan.cases, focus.caseId, !caseOn) })}>
          {caseOn ? "Remove case" : "Add case"}
        </Button>
      </div>
    </div>
  );
}

/** Count, estimate, readiness, and review, pinned above the matrix while it scrolls. */
function PlanStrip({ plan, total, est, errors, onReview }: { plan: Plan; total: number; est: Estimate; errors: string[]; onReview: () => void }) {
  const { fresh } = useFreshness();
  return (
    <div className="sticky top-12 z-10 flex flex-wrap items-center gap-x-6 gap-y-3 rounded-lg border border-line bg-surface/95 px-4 py-3 backdrop-blur-md lg:top-14">
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="num text-[22px] leading-none font-medium tracking-[-0.02em]">{count(total)}</span>
          <span className="text-[12.5px] text-fg-3">attempts · serial</span>
        </div>
        <div className="mt-1 truncate font-mono text-[11px] text-fg-3">{formula(plan).join(" × ")}</div>
      </div>
      <div className="flex gap-5">
        <div>
          <div className="num text-[14px] font-medium">{est.seconds === null ? "—" : `≈ ${duration(est.seconds)}`}</div>
          <div className="text-[11px] text-fg-3">Runner time, est.</div>
        </div>
        <div>
          <div className="num text-[14px] font-medium">{est.cost === null ? "—" : `≈ ${usd(est.cost)}`}</div>
          <div className="text-[11px] text-fg-3">API cost, est.</div>
        </div>
      </div>
      <div className="flex min-w-[240px] flex-1 items-center gap-3">
        <GateSummary fresh={fresh} compact className="min-w-0 flex-1" />
        {fresh.state !== "fresh" && <PreflightButton fresh={fresh} />}
      </div>
      <div className="ml-auto flex items-center gap-3">
        {errors[0] && <span className="text-[12px] text-warn">{errors[0]}</span>}
        <Button variant="primary" disabled={errors.length > 0} onClick={onReview}>
          Review
        </Button>
      </div>
    </div>
  );
}

export default function MatrixPlanner() {
  const history = useHistory();
  const [plan, setPlan] = useState<Plan>({ cases: [...DEMO_CASES], techniques: ["allStepsAtOnce"], models: ["gpt-6-luna", "glm-4.7-flash:latest"], repetitions: 1, apiModel: "", verificationModel: "" });
  const [focus, setFocus] = useState<{ row: number; col: number } | null>(null);
  const [review, setReview] = useState(false);
  const table = useRef<HTMLTableElement>(null);
  const update = (next: Partial<Plan>) => setPlan((p) => ({ ...p, ...next }));
  const total = plannedCount(plan);
  const errors = validate(plan);
  const est = estimate(plan, history);

  if (!history) return <div className="h-[560px] animate-pulse rounded-lg bg-surface" />;
  const models = history.models.map((m) => m.id);
  const perCell = plan.techniques.length * plan.repetitions;

  const moveFocus = (row: number, col: number) => {
    const r = Math.max(0, Math.min(ROWS.length - 1, row));
    const c = Math.max(0, Math.min(models.length - 1, col));
    setFocus({ row: r, col: c });
    table.current?.querySelector<HTMLButtonElement>(`[data-cell="${r}-${c}"]`)?.focus();
  };
  const onCellKey = (e: KeyboardEvent<HTMLButtonElement>, row: number, col: number) => {
    const moves: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    const move = moves[e.key];
    if (move) {
      e.preventDefault();
      moveFocus(row + move[0], col + move[1]);
    } else if (e.key === "Home") {
      e.preventDefault();
      moveFocus(row, 0);
    } else if (e.key === "End") {
      e.preventDefault();
      moveFocus(row, models.length - 1);
    }
  };
  const tabRow = focus?.row ?? 0;
  const tabCol = focus?.col ?? 0;

  const colTime = (model: string) =>
    plan.cases.reduce((sum, caseId) => sum + plan.techniques.reduce((s, t) => s + (history.caseMedian(model, t, caseId) ?? history.combo(model, t).medianS ?? 0), 0), 0) * plan.repetitions;

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-[12.5px] text-fg-3">
          A campaign runs every selected case with every selected model. Pick rows and columns; cells show recorded Ground Truth history (passed of known) under the selected techniques.
        </p>
        <ScenarioSwitch />
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Techniques">
          <span className="label !text-[10px]">Technique</span>
          {TECHNIQUES.map((t) => {
            const on = plan.techniques.includes(t.id);
            return (
              <Tip key={t.id} content={t.blurb}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => update({ techniques: toggle<Technique>(plan.techniques, t.id, !on) })}
                  className={clsx("h-7 cursor-pointer rounded-md border px-2.5 text-[12.5px]", on ? "border-accent-line bg-accent-soft text-fg" : "border-line text-fg-3 hover:text-fg")}
                >
                  {techniqueLabel(t.id)}
                </button>
              </Tip>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <span className="label !text-[10px]">Repetitions</span>
          <RepetitionsInput value={plan.repetitions} onChange={(repetitions) => update({ repetitions })} presets={[1, 5]} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="label !text-[10px]">Select from history</span>
          {QUICK.map((q) => {
            const ids = quickCases(q.id, plan, history);
            return (
              <Tip key={q.id} content={`${q.hint} ${ids.length} now.`}>
                <button type="button" disabled={!ids.length} onClick={() => update({ cases: ids })} className="h-7 cursor-pointer rounded-md border border-line px-2.5 text-[12.5px] text-fg-2 hover:border-line-strong hover:text-fg disabled:cursor-not-allowed disabled:opacity-40">
                  {q.label} <span className="num text-fg-3">{ids.length}</span>
                </button>
              </Tip>
            );
          })}
        </div>
      </div>

      <PlanStrip plan={plan} total={total} est={est} errors={errors} onReview={() => setReview(true)} />

      <div className="grid gap-4">
        <div className="min-w-0 rounded-lg border border-line bg-surface">
          <div className="overflow-x-auto">
            <table ref={table} className="w-full min-w-[940px] table-fixed border-separate border-spacing-0 text-[12.5px]" aria-label="Cases by debug model, with recorded history">
              <colgroup>
                <col className="w-[210px]" />
                {history.models.map((m) => (
                  <col key={m.id} />
                ))}
              </colgroup>
              <thead>
                <tr>
                  <th scope="col" className="sticky left-0 z-[2] w-[210px] border-b border-line bg-surface px-3 py-2 text-left align-bottom font-normal">
                    <div className="flex items-center gap-2">
                      <Checkbox label="All cases" checked={plan.cases.length === CATALOG.length} indeterminate={plan.cases.length > 0} onChange={(next) => update({ cases: next ? CATALOG : [] })} />
                      <span className="label !text-[10px]">
                        Cases {plan.cases.length}/{CATALOG.length}
                      </span>
                    </div>
                  </th>
                  {history.models.map((m) => {
                    const on = plan.models.includes(m.id);
                    return (
                      <th key={m.id} scope="col" className={clsx("border-b border-line px-1.5 py-2 text-left align-bottom font-normal", on && "bg-accent-soft")}>
                        <div className="grid min-w-0 gap-1.5">
                          <span className="flex items-center gap-1.5">
                            <Checkbox label={`Include ${displayModel(m.id)}`} checked={on} onChange={(next) => update({ models: toggle(plan.models, m.id, next) })} />
                            {m.notInstalled && <NotInstalled iconOnly />}
                          </span>
                          <ModelName stats={m} className={clsx("max-w-full text-[11.5px]", on ? "text-fg" : "text-fg-2")} />
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {FAMILIES.map((f) => {
                  const ids = f.cases.map((c) => c.id);
                  const on = ids.filter((id) => plan.cases.includes(id)).length;
                  return [
                    <tr key={`family-${f.family}`}>
                      <th scope="rowgroup" colSpan={1} className="sticky left-0 z-[1] border-t border-line bg-surface px-3 pt-2.5 pb-1 text-left font-normal">
                        <div className="flex items-center gap-2">
                          <Checkbox label={`All ${humanize(f.family)} cases`} checked={on === ids.length} indeterminate={on > 0} onChange={(next) => update({ cases: next ? [...new Set([...plan.cases, ...ids])] : plan.cases.filter((id) => !ids.includes(id)) })} />
                          <FamilyName family={f.family} ids={ids} className="text-[12.5px] font-medium text-fg" />
                        </div>
                      </th>
                      <td colSpan={models.length} className="border-t border-line" />
                    </tr>,
                    ...f.cases.map((c) => {
                      const row = ROWS.indexOf(c.id);
                      const caseOn = plan.cases.includes(c.id);
                      return (
                        <tr key={c.id}>
                          <th scope="row" className="sticky left-0 z-[1] bg-surface py-[3px] pr-2 pl-[34px] text-left font-normal">
                            <div className="flex min-w-0 items-center gap-2">
                              <Checkbox label={`Include ${c.id}`} checked={caseOn} onChange={(next) => update({ cases: toggle(plan.cases, c.id, next) })} />
                              <CaseName id={c.id} className={clsx("ident text-[12px]", caseOn ? "text-fg" : "text-fg-3")} />
                            </div>
                          </th>
                          {history.models.map((m, col) => {
                            const planned = caseOn && plan.models.includes(m.id);
                            const cell = history.cell(m.id, c.id, plan.techniques);
                            const focused = focus?.row === row && focus?.col === col;
                            return (
                              <td key={m.id} className="p-[2px]">
                                <button
                                  type="button"
                                  data-cell={`${row}-${col}`}
                                  tabIndex={row === tabRow && col === tabCol ? 0 : -1}
                                  onClick={() => setFocus({ row, col })}
                                  onKeyDown={(e) => onCellKey(e, row, col)}
                                  aria-label={`${displayModel(m.id)}, ${c.id}: ${planned ? `planned, ${perCell} attempts` : "not planned"}; history ${cell.known ? `${cell.passed} of ${cell.known} passed` : "none"}`}
                                  className={clsx(
                                    "flex h-8 w-full cursor-pointer items-center rounded-[4px] border transition-colors",
                                    planned ? "border-accent-line bg-accent-soft" : "border-transparent hover:bg-surface-2",
                                    focused && "ring-2 ring-fg ring-offset-1 ring-offset-surface",
                                  )}
                                >
                                  <HistoryCell cell={cell} planned={planned} />
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      );
                    }),
                  ];
                })}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row" className="sticky left-0 z-[1] border-t border-line bg-surface px-3 py-2 text-left font-normal">
                    <span className="label !text-[10px]">Runner time · est.</span>
                  </th>
                  {history.models.map((m) => (
                    <td key={m.id} className="num border-t border-line px-1.5 py-2 text-[11.5px] text-fg-2">
                      {plan.models.includes(m.id) && plan.cases.length ? `≈ ${duration(colTime(m.id))}` : <span className="text-fg-3">—</span>}
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-line px-3 py-2 text-[11.5px] text-fg-3">
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-[2px] border border-accent-line bg-accent-soft" /> Planned: {perCell} {perCell === 1 ? "attempt" : "attempts"} per cell
            </span>
            <span>
              <span className="num text-fg-2">3/5</span> history: passed of known, all sources
            </span>
            <span>
              <span className="num text-fg-2">—</span> no recorded attempt
            </span>
            <span>Arrow keys move between cells.</span>
          </div>
        </div>

        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="rounded-lg border border-line bg-surface p-4">
            <div className="label mb-2">Selected cell</div>
            <Inspector focus={focus ? { model: models[focus.col], caseId: ROWS[focus.row] } : null} plan={plan} history={history} onPlan={update} />
          </div>
          <div className="grid gap-2 rounded-lg border border-line bg-surface p-4">
            <div className="label">About the estimate</div>
            <EstimateNote est={est} />
            {!plan.models.length && <p className="text-[12px] text-fg-3">No model column selected: each case runs its configured default model.</p>}
            <p className="text-[12px] text-fg-3">The column footer sums recorded per-case medians for that model; cases without history borrow the model's median.</p>
          </div>
        </div>
      </div>
      <ReviewDialog plan={plan} open={review} onOpenChange={setReview} />
    </div>
  );
}
