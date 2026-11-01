import clsx from "clsx";
import { Check } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui";
import { caseFamily, humanize } from "@/lib/cases";
import { techniqueLabel } from "@/lib/explore";
import { count, duration, usd } from "@/lib/format";
import { CheckMark, GROUPS, LiveAnnouncer, ScenarioSwitch, freshnessLine, readiness, useFreshness } from "../environment/readiness";
import {
  CATALOG,
  CasePicker,
  EstimateNote,
  FAMILIES,
  FixedModels,
  GateSummary,
  ModelChip,
  ModelList,
  PreflightButton,
  RepetitionsInput,
  ReviewDialog,
  TechniquePicker,
  attemptAt,
  attemptLabel,
  effectiveModels,
  estimate,
  plannedCount,
  useHistory,
  validate,
  type Plan,
} from "./plan";

type StepId = "models" | "cases" | "technique" | "repetitions" | "readiness" | "review";
const STEP_IDS: StepId[] = ["models", "cases", "technique", "repetitions", "readiness", "review"];
const TITLES: Record<StepId, string> = {
  models: "Debug models",
  cases: "Cases",
  technique: "Technique",
  repetitions: "Repetitions",
  readiness: "Readiness",
  review: "Review",
};

function Tally({ plan, reached }: { plan: Plan; reached: number }) {
  const parts: { label: string; value: string; at: number }[] = [
    { label: "models", value: plan.models.length ? String(plan.models.length) : "default", at: 0 },
    { label: "cases", value: String(plan.cases.length), at: 1 },
    { label: plan.techniques.length === 1 ? "technique" : "techniques", value: String(plan.techniques.length), at: 2 },
    { label: "repetitions", value: String(plan.repetitions), at: 3 },
  ];
  const known = reached > 3;
  return (
    <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1 font-mono text-[12.5px]" aria-label="Planned attempts so far">
      {parts.map((p, i) => (
        <span key={p.label} className="inline-flex items-baseline gap-2.5">
          {i > 0 && <span className="text-fg-3">×</span>}
          <span className={clsx(reached > p.at ? "text-fg" : "text-fg-3")}>
            <span className="num">{reached > p.at ? p.value : "?"}</span> <span className="text-fg-3">{p.label}</span>
          </span>
        </span>
      ))}
      <span className="text-fg-3">=</span>
      <span className={clsx("num text-[15px] font-medium", known ? "text-fg" : "text-fg-3")}>{known ? count(plannedCount(plan)) : "…"}</span>
    </div>
  );
}

function Marker({ index, state }: { index: number; state: "done" | "active" | "todo" }) {
  return (
    <span
      aria-hidden
      className={clsx(
        "relative z-[1] grid size-6 shrink-0 place-items-center rounded-full font-mono text-[11px] font-medium",
        state === "active" && "bg-accent text-accent-ink",
        state === "done" && "border border-line-strong bg-surface text-fg-2",
        state === "todo" && "border border-dashed border-line-strong bg-bg text-fg-3",
      )}
    >
      {state === "done" ? <Check className="size-3" strokeWidth={2.5} /> : index + 1}
    </span>
  );
}

function Step({ id, index, current, summary, onEdit, children, last }: { id: StepId; index: number; current: number; summary: ReactNode; onEdit: () => void; children: ReactNode; last?: boolean }) {
  const state = index < current ? "done" : index === current ? "active" : "todo";
  return (
    <li className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-x-4" aria-current={state === "active" ? "step" : undefined}>
      {!last && <span aria-hidden className="absolute top-7 bottom-0 left-[11.5px] w-px bg-line-strong" />}
      <Marker index={index} state={state} />
      <div className={clsx("min-w-0", last ? "pb-1" : "pb-7")}>
        <div className="flex min-h-6 flex-wrap items-center justify-between gap-x-4 gap-y-1">
          <h3 id={`launch-b-${id}`} className={clsx("text-[14px] font-medium", state === "todo" && "text-fg-3")}>
            {TITLES[id]}
          </h3>
          {state === "done" && (
            <button type="button" onClick={onEdit} className="cursor-pointer text-[12.5px] text-fg-3 hover:text-fg">
              Edit
            </button>
          )}
        </div>
        {state === "done" && <div className="mt-1 text-[12.5px] text-fg-2">{summary}</div>}
        {state === "active" && (
          <section aria-labelledby={`launch-b-${id}`} className="mt-3">
            {children}
          </section>
        )}
      </div>
    </li>
  );
}

function ReadinessStep() {
  const { fresh, active, latest } = useFreshness();
  const shown = active ?? null;
  const checks = latest?.checks ?? [];
  return (
    <div className="grid gap-4">
      <p className="text-[13px] text-fg-2">The server refuses a campaign unless the lane passed preflight in the last 20 minutes. Preflight only checks; it changes nothing.</p>
      <div className="grid gap-3 rounded-md border border-line p-3">
        <GateSummary fresh={fresh} />
        <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-3">
          {GROUPS.map((g) => {
            const inGroup = (shown ? shown.done : checks).filter((c) => c.group === g.id);
            const running = shown?.current?.group === g.id;
            const worst = inGroup.find((c) => c.level === "block") ?? inGroup.find((c) => c.level === "warn") ?? inGroup[0];
            const total = checks.filter((c) => c.group === g.id).length || inGroup.length;
            const doneAll = shown ? inGroup.length === total && total > 0 : inGroup.length > 0;
            return (
              <li key={g.id} className="flex min-w-0 items-center gap-2 text-[12.5px]">
                <CheckMark running={running} pending={!running && !doneAll} level={worst?.level} />
                <span className={clsx("truncate", doneAll || running ? "text-fg-2" : "text-fg-3")}>{g.label}</span>
              </li>
            );
          })}
        </ul>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <PreflightButton fresh={fresh} />
        {fresh.state === "blocked" && (
          <Button size="sm" variant="ghost" onClick={readiness.prepare}>
            Prepare environment <span className="font-mono text-[10px] tracking-[0.06em] text-fg-3 uppercase">Demo</span>
          </Button>
        )}
      </div>
    </div>
  );
}

function ReviewStep({ plan, onStart }: { plan: Plan; onStart: () => void }) {
  const history = useHistory();
  const { canLaunch } = useFreshness();
  const est = estimate(plan, history);
  const total = plannedCount(plan);
  const errors = validate(plan);
  const perCase = total / Math.max(1, plan.cases.length);
  const byFamily = FAMILIES.map((f) => ({ family: f.family, ids: f.cases.map((c) => c.id).filter((id) => plan.cases.includes(id)) })).filter((f) => f.ids.length);
  return (
    <div className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <div className="label">Attempts</div>
          <div className="num mt-1 text-[22px] font-medium">{count(total)}</div>
          <div className="text-[12px] text-fg-3">{perCase} per case, serial</div>
        </div>
        <div>
          <div className="label">Runner time</div>
          <div className="num mt-1 text-[22px] font-medium">{est.seconds === null ? "—" : `≈ ${duration(est.seconds)}`}</div>
          <div className="text-[12px] text-fg-3">Estimate</div>
        </div>
        <div>
          <div className="label">API cost</div>
          <div className="num mt-1 text-[22px] font-medium">{est.cost === null ? "—" : `≈ ${usd(est.cost)}`}</div>
          <div className="text-[12px] text-fg-3">Estimate</div>
        </div>
      </div>
      <EstimateNote est={est} />

      <div className="grid gap-2">
        <div className="label">Every case runs</div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px] text-fg-2">
          {effectiveModels(plan).map((m) => (
            <ModelChip key={m ?? "default"} id={m} className="text-fg" />
          ))}
          <span className="text-fg-3">·</span>
          <span>{plan.techniques.map(techniqueLabel).join(", ")}</span>
          <span className="text-fg-3">·</span>
          <span className="num">
            {plan.repetitions} {plan.repetitions === 1 ? "repetition" : "repetitions"}
          </span>
        </div>
      </div>

      <div className="grid gap-2">
        <div className="label">Cases by scenario</div>
        <ul className="grid gap-x-6 sm:grid-cols-2">
          {byFamily.map((f) => (
            <li key={f.family} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-t border-line py-1.5 text-[12.5px]">
              <span className="shrink-0 text-fg">{humanize(f.family)}</span>
              <span className="ident min-w-0 text-right text-[11.5px] text-fg-3">{f.ids.map((id) => caseFamily(id).variant).join(" · ")}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-1.5">
        <div className="label">First attempts</div>
        <ol className="grid gap-0.5 font-mono text-[11.5px] text-fg-2">
          {Array.from({ length: Math.min(4, total) }, (_, i) => attemptAt(plan, i)).map((a) => (
            <li key={a.sequence} className="truncate">
              <span className="text-fg-3">{String(a.sequence).padStart(4, "0")} </span>
              {attemptLabel(a)}
            </li>
          ))}
          {total > 4 && <li className="text-fg-3">… {count(total - 4)} more in the review</li>}
        </ol>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
        <Button variant="primary" onClick={onStart} disabled={errors.length > 0}>
          Review and start
        </Button>
        <span className={clsx("text-[12.5px]", canLaunch ? "text-fg-3" : "text-warn")}>{canLaunch ? "Readiness is fresh." : "Starting needs a fresh ready preflight."}</span>
      </div>
    </div>
  );
}

export default function GuidedSteps() {
  const history = useHistory();
  const { fresh } = useFreshness();
  const [plan, setPlan] = useState<Plan>({ cases: [], techniques: ["allStepsAtOnce"], models: [], repetitions: 1, apiModel: "", verificationModel: "" });
  const [current, setCurrent] = useState(0);
  const [reached, setReached] = useState(0);
  const [review, setReview] = useState(false);
  const update = (next: Partial<Plan>) => setPlan((p) => ({ ...p, ...next }));
  const go = (index: number) => {
    setCurrent(index);
    setReached((r) => Math.max(r, index));
    // Bring the newly opened step's heading into view once it renders.
    window.requestAnimationFrame(() => document.getElementById("launch-b-" + STEP_IDS[index])?.scrollIntoView({ block: "nearest" }));
  };
  const next = () => go(current + 1);

  const continueRow = (enabled: boolean, label = "Continue", note?: ReactNode) => (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <Button variant="primary" onClick={next} disabled={!enabled}>
        {label}
      </Button>
      {note && <span className="text-[12.5px] text-fg-3">{note}</span>}
    </div>
  );

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tally plan={plan} reached={reached} />
        <ScenarioSwitch />
      </div>
      <div className="rounded-lg border border-line bg-surface px-4 py-5 sm:px-6">
        <ol className="mx-auto grid max-w-[880px]">
          <Step id="models" index={0} current={current} onEdit={() => go(0)} summary={plan.models.length ? <span className="flex flex-wrap gap-x-3 gap-y-1">{plan.models.map((m) => <ModelChip key={m} id={m} />)}</span> : "Each case's configured default model"}>
            <ModelList history={history} value={plan.models} onChange={(models) => update({ models })} />
            {continueRow(true, plan.models.length ? `Continue with ${plan.models.length} ${plan.models.length === 1 ? "model" : "models"}` : "Continue with case defaults")}
          </Step>
          <Step id="cases" index={1} current={current} onEdit={() => go(1)} summary={plan.cases.length === CATALOG.length ? `All ${CATALOG.length} cases` : `${plan.cases.length} cases`}>
            <CasePicker value={plan.cases} onChange={(cases) => update({ cases })} />
            {continueRow(plan.cases.length > 0, "Continue", plan.cases.length ? `${plan.cases.length} selected` : "Select at least one case.")}
          </Step>
          <Step id="technique" index={2} current={current} onEdit={() => go(2)} summary={plan.techniques.map(techniqueLabel).join(", ")}>
            <TechniquePicker history={history} plan={plan} onChange={(techniques) => update({ techniques })} />
            {continueRow(plan.techniques.length > 0)}
          </Step>
          <Step id="repetitions" index={3} current={current} onEdit={() => go(3)} summary={`${plan.repetitions}× · knowledge ${plan.apiModel.trim() || "default"} · verifier ${plan.verificationModel.trim() || "default"}`}>
            <div className="grid gap-5">
              <RepetitionsInput value={plan.repetitions} onChange={(repetitions) => update({ repetitions })} />
              <FixedModels plan={plan} onChange={update} />
            </div>
            {continueRow(validate(plan).length === 0, "Continue", validate(plan)[0])}
          </Step>
          <Step id="readiness" index={4} current={current} onEdit={() => go(4)} summary={freshnessLine(fresh)}>
            <ReadinessStep />
            {continueRow(true, fresh.state === "fresh" ? "Continue" : "Continue to review", fresh.state === "fresh" ? undefined : "You can review now and run preflight before starting.")}
          </Step>
          <Step id="review" index={5} current={current} onEdit={() => go(5)} summary="" last>
            <ReviewStep plan={plan} onStart={() => setReview(true)} />
          </Step>
        </ol>
      </div>
      <ReviewDialog plan={plan} open={review} onOpenChange={setReview} />
    </div>
  );
}

