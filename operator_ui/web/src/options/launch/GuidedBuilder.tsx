import clsx from "clsx";
import { ArrowRight, Check } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { api } from "@/api/client";
import { Button, Tag } from "@/components/ui";
import { techniqueLabel } from "@/lib/explore";
import { count, duration, usd } from "@/lib/format";
import { CheckMark, GROUPS, LANE, LiveAnnouncer, ScenarioSwitch, freshnessLine, readiness, useFreshness } from "../environment/readiness";
import {
  AttemptList,
  CATALOG,
  CaseName,
  CasePicker,
  Disclosure,
  EMPTY_PLAN,
  EstimateNote,
  FAMILIES,
  FamilyName,
  FixedModels,
  GateSummary,
  LaunchNotes,
  MAX_ATTEMPTS,
  ModelChip,
  ModelList,
  PreflightButton,
  ReadinessGate,
  RepetitionsInput,
  RequestPreview,
  TechniquePicker,
  effectiveModels,
  estimate,
  formula,
  plannedCount,
  requestBody,
  useHistory,
  validate,
  type Plan,
} from "./plan";

// New campaign: one decision per step on the left, and a plan rail on the
// right that totals everything chosen so far and owns the launch action. The
// final step confirms what will run; it does not repeat the rail's totals.

type StepId = "models" | "cases" | "technique" | "repetitions" | "confirm";
const STEP_IDS: StepId[] = ["models", "cases", "technique", "repetitions", "confirm"];
const LAST = STEP_IDS.length - 1;
const TITLES: Record<StepId, string> = {
  models: "Debug models",
  cases: "Cases",
  technique: "Technique",
  repetitions: "Repetitions",
  confirm: "Confirm",
};
/** The step that edits each part of the rail's breakdown (formula order). */
const FORMULA_STEP: StepId[] = ["cases", "models", "technique", "repetitions"];

const STARTERS: { id: string; label: string; hint: string; plan: Partial<Plan>; open?: StepId }[] = [
  { id: "catalog", label: "Full case catalog", hint: "All available cases · all at once · 1×", plan: { cases: CATALOG, techniques: ["allStepsAtOnce"], repetitions: 1, apiModel: "", verificationModel: "" }, open: "models" },
];

interface Action {
  label: string;
  onClick: () => void;
  disabled: boolean;
  demo?: boolean;
}

// ---------------------------------------------------------------- steps

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

function Step({ id, index, state, summary, onEdit, children }: { id: StepId; index: number; state: "done" | "active" | "todo"; summary: ReactNode; onEdit: () => void; children: ReactNode }) {
  const last = index === LAST;
  return (
    <li className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-x-4" aria-current={state === "active" ? "step" : undefined}>
      {!last && <span aria-hidden className="absolute top-7 bottom-0 left-[11.5px] w-px bg-line-strong" />}
      <Marker index={index} state={state} />
      <div className={clsx("min-w-0", last ? "pb-1" : "pb-7")}>
        <div className="flex min-h-6 flex-wrap items-center justify-between gap-x-4 gap-y-1">
          <h3 id={`launch-step-${id}`} tabIndex={-1} className={clsx("scroll-mt-20 text-[14px] font-medium outline-none", state === "todo" && "text-fg-3")}>
            {TITLES[id]}
          </h3>
          {state === "done" && (
            <button type="button" onClick={onEdit} aria-label={`Edit ${TITLES[id].toLowerCase()}`} className="cursor-pointer text-[12.5px] text-fg-3 hover:text-fg">
              Edit
            </button>
          )}
        </div>
        {state === "done" && <div className="mt-1 min-w-0 text-[12.5px] text-fg-2">{summary}</div>}
        {state === "active" && (
          <section aria-labelledby={`launch-step-${id}`} className="mt-3">
            {children}
          </section>
        )}
      </div>
    </li>
  );
}

/** Readiness groups at a glance; the rail carries the gate itself. */
function ReadinessGroups() {
  const { fresh, active, latest } = useFreshness();
  const checks = latest?.checks ?? [];
  return (
    <div className="grid gap-2.5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="label">Readiness · {LANE.profile}</span>
        {fresh.state === "blocked" && (
          <Button size="sm" variant="ghost" onClick={readiness.prepare}>
            Prepare environment <span className="font-mono text-[10px] tracking-[0.06em] text-fg-3 uppercase">Demo</span>
          </Button>
        )}
      </div>
      <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-3">
        {GROUPS.map((g) => {
          const inGroup = (active ? active.done : checks).filter((c) => c.group === g.id);
          const running = active?.current?.group === g.id;
          const worst = inGroup.find((c) => c.level === "block") ?? inGroup.find((c) => c.level === "warn") ?? inGroup[0];
          const total = checks.filter((c) => c.group === g.id).length || inGroup.length;
          const doneAll = active ? inGroup.length === total && total > 0 : inGroup.length > 0;
          return (
            <li key={g.id} className="flex min-w-0 items-center gap-2 text-[12.5px]">
              <CheckMark running={running} pending={!running && !doneAll} level={worst?.level} />
              <span className={clsx("truncate", doneAll || running ? "text-fg-2" : "text-fg-3")}>{g.label}</span>
            </li>
          );
        })}
      </ul>
      {/* On phones the bottom bar shows the gate without its explanation. */}
      <p className="text-[12px] leading-snug text-fg-3 xl:hidden">{freshnessLine(fresh)}</p>
    </div>
  );
}

function ConfirmStep({ plan }: { plan: Plan }) {
  const history = useHistory();
  const est = estimate(plan, history);
  const total = plannedCount(plan);
  const byFamily = FAMILIES.map((f) => ({ family: f.family, ids: f.cases.map((c) => c.id).filter((id) => plan.cases.includes(id)) })).filter((f) => f.ids.length);
  return (
    <div className="grid gap-5">
      <p className="text-[13px] text-fg-2">
        {count(total)} {total === 1 ? "attempt runs" : "attempts run"} one at a time on <span className="ident">{LANE.profile}</span> through the canonical runner, in this order.
      </p>

      {/* The rail holds the estimate on wide screens; phones see it here. */}
      <div className="grid gap-2 xl:hidden">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="label">Runner time</div>
            <div className="num mt-1 text-[17px] font-medium">{est.seconds === null ? "—" : `≈ ${duration(est.seconds)}`}</div>
          </div>
          <div>
            <div className="label">API cost</div>
            <div className="num mt-1 text-[17px] font-medium">{est.cost === null ? "—" : `≈ ${usd(est.cost)}`}</div>
          </div>
        </div>
        <EstimateNote est={est} />
      </div>

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
        <div className="text-[12px] text-fg-3">
          Knowledge <span className="ident text-fg-2">{plan.apiModel.trim() || "case default"}</span> · verifier <span className="ident text-fg-2">{plan.verificationModel.trim() || "case default"}</span>
        </div>
      </div>

      <div className="grid gap-2">
        <div className="label">Cases by scenario</div>
        <ul className="grid gap-x-6 sm:grid-cols-2">
          {byFamily.map((f) => (
            <li key={f.family} className="flex min-w-0 items-baseline justify-between gap-x-3 border-t border-line py-1.5 text-[12.5px]">
              <FamilyName family={f.family} ids={f.ids} side="bottom" className="shrink-0 text-fg" />
              <span className="flex min-w-0 flex-wrap justify-end gap-x-1.5 text-[11.5px] text-fg-3">
                {f.ids.map((id, i) => (
                  <span key={id} className="inline-flex min-w-0 items-baseline gap-1.5">
                    {i > 0 && <span aria-hidden>·</span>}
                    <CaseName id={id} side="bottom" className="ident" />
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-2">
        <div className="label">Run order</div>
        <AttemptList plan={plan} />
      </div>

      <ReadinessGroups />

      <Disclosure title="Request and first runner invocation">
        <RequestPreview plan={plan} />
      </Disclosure>

      <LaunchNotes />
      <p className="hidden items-center gap-1.5 border-t border-line pt-3 text-[12.5px] text-fg-3 xl:flex">
        Start from the plan rail once readiness is fresh <ArrowRight className="size-3.5" strokeWidth={1.75} />
      </p>
    </div>
  );
}

// ---------------------------------------------------------------- plan rail

function ActionButton({ action, className }: { action: Action; className?: string }) {
  return (
    <Button variant="primary" className={className} disabled={action.disabled} onClick={action.onClick}>
      {action.label}
      {action.demo && <span className="font-mono text-[10px] tracking-[0.06em] uppercase opacity-60">Demo</span>}
    </Button>
  );
}

function PlanRail({ plan, action, onEditPart }: { plan: Plan; action: Action; onEditPart: (step: StepId) => void }) {
  const history = useHistory();
  const total = plannedCount(plan);
  const errors = validate(plan);
  const est = estimate(plan, history);
  const parts = formula(plan);
  return (
    <div className="grid gap-5 rounded-lg border border-line bg-surface p-4">
      <div>
        <div className="flex items-center justify-between">
          <span className="label">Planned attempts</span>
          <Tag>Serial</Tag>
        </div>
        <div className="num mt-2 text-[34px] leading-none font-medium tracking-[-0.03em]" aria-live="polite">
          {count(total)}
        </div>
        <ul className="mt-3 grid gap-0.5 font-mono text-[12px] text-fg-2">
          {parts.map((part, i) => (
            <li key={part} className="flex gap-2">
              <span className="w-3 text-fg-3">{i === 0 ? "" : "×"}</span>
              <button type="button" onClick={() => onEditPart(FORMULA_STEP[i])} aria-label={`${part}: edit ${TITLES[FORMULA_STEP[i]].toLowerCase()}`} className="min-w-0 cursor-pointer truncate text-left hover:text-fg hover:underline hover:decoration-line-strong hover:underline-offset-2">
                {part}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface-3" role="meter" aria-label="Share of the attempt limit" aria-valuemin={0} aria-valuemax={MAX_ATTEMPTS} aria-valuenow={total}>
          <div className={clsx("h-full rounded-full", total > MAX_ATTEMPTS ? "bg-warn" : "bg-fg-3")} style={{ width: `${Math.min(1, total / MAX_ATTEMPTS) * 100}%` }} />
        </div>
        <div className="num mt-1 text-[11.5px] text-fg-3">Limit {count(MAX_ATTEMPTS)} per campaign</div>
      </div>

      <div className="grid gap-2 border-t border-line pt-4">
        <span className="label">Estimate</span>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="num text-[17px] font-medium">{est.seconds === null ? "—" : `≈ ${duration(est.seconds)}`}</div>
            <div className="text-[11.5px] text-fg-3">Runner time</div>
          </div>
          <div>
            <div className="num text-[17px] font-medium">{est.cost === null ? "—" : `≈ ${usd(est.cost)}`}</div>
            <div className="text-[11.5px] text-fg-3">API cost</div>
          </div>
        </div>
        <EstimateNote est={est} />
      </div>

      <div className="border-t border-line pt-4">
        <ReadinessGate />
      </div>

      <div className="grid gap-2 border-t border-line pt-4">
        {errors.length > 0 && total > 0 && (
          <ul className="grid gap-0.5 text-[12px] text-warn">
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        )}
        {!plan.cases.length && <p className="text-[12px] text-fg-3">Select cases to plan attempts.</p>}
        <ActionButton action={action} className="w-full" />
      </div>
    </div>
  );
}

function MobileBar({ plan, action }: { plan: Plan; action: Action }) {
  const { fresh } = useFreshness();
  const total = plannedCount(plan);
  return (
    <div className="sticky bottom-0 z-10 -mx-4 border-t border-line bg-bg/90 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 xl:hidden">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <div className="num text-[15px] font-medium">
            {count(total)} <span className="text-[12.5px] font-normal text-fg-3">attempts</span>
          </div>
          <GateSummary fresh={fresh} compact className="mt-1 max-w-56" />
        </div>
        {fresh.state !== "fresh" && <PreflightButton fresh={fresh} />}
        <ActionButton action={{ ...action, label: action.label.split(" ")[0] }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- page

/** Live campaigns are started only from the final reviewed plan. */
function useStart() {
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const start = (plan: Plan) => {
    setError("");
    setStarting(true);
    if (!api.isLive) {
      timer.current = window.setTimeout(() => navigate("/execution"), 700);
      return;
    }
    void api.startCampaign(requestBody(plan)).then((job) => {
      navigate(`/execution?job=${encodeURIComponent(job.id)}`);
    }).catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : "Campaign could not be started.");
    }).finally(() => setStarting(false));
  };
  return { starting, start, error };
}

export default function GuidedBuilder() {
  const history = useHistory();
  const { canLaunch } = useFreshness();
  const { starting, start, error: startError } = useStart();
  const casesQuery = useQuery({ queryKey: ["operator-cases"], queryFn: api.cases, enabled: api.isLive, staleTime: 60_000, retry: 0 });
  const catalog = api.isLive ? (casesQuery.data?.map((item) => item.id) ?? []) : CATALOG;
  const [plan, setPlan] = useState<Plan>(EMPTY_PLAN);
  const [current, setCurrent] = useState(0);
  const [reached, setReached] = useState(0);
  const update = (next: Partial<Plan>) => setPlan((p) => ({ ...p, ...next }));

  const go = (index: number) => {
    setCurrent(index);
    setReached((r) => Math.max(r, index));
    // Move focus to the opened step's heading once it renders, for keyboard
    // and screen-reader users, and bring it into view.
    window.requestAnimationFrame(() => {
      const heading = document.getElementById("launch-step-" + STEP_IDS[index]);
      heading?.focus({ preventScroll: true });
      heading?.scrollIntoView({ block: "nearest" });
    });
  };
  const returning = reached >= LAST;
  const next = () => go(returning ? LAST : current + 1);
  const stateOf = (index: number) => (index === current ? "active" : index < current || (index <= reached && index < LAST) ? "done" : "todo");

  const applyStarter = (starter: (typeof STARTERS)[number]) => {
    update({ ...starter.plan, ...(starter.id === "catalog" ? { cases: catalog } : {}) });
    setReached(LAST);
    go(STEP_IDS.indexOf(starter.open ?? "confirm"));
  };
  const blank = () => {
    setPlan(EMPTY_PLAN);
    setReached(0);
    go(0);
  };

  const total = plannedCount(plan);
  const errors = validate(plan);
  const noun = total === 1 ? "attempt" : "attempts";
  const action: Action =
    current === LAST
      ? {
          label: starting ? "Starting…" : `Start ${count(total)} ${noun}`,
          onClick: () => start(plan),
          disabled: starting || errors.length > 0 || !canLaunch,
          demo: !api.isLive,
        }
      : { label: `Review ${count(total)} ${noun}`, onClick: () => go(LAST), disabled: errors.length > 0 };

  const continueRow = (enabled: boolean, label = "Continue", note?: ReactNode) => (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <Button variant="primary" onClick={next} disabled={!enabled}>
        {returning ? "Continue to confirm" : label}
      </Button>
      {note && <span className="text-[12.5px] text-fg-3">{note}</span>}
    </div>
  );

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-fg-3">
          <span>Start from</span>
          {STARTERS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => applyStarter(s)}
              className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-line px-2.5 text-fg-2 hover:border-line-strong hover:text-fg"
            >
              {s.label}
              <span className="text-fg-3">{s.hint}</span>
            </button>
          ))}
          <button type="button" onClick={blank} className="h-7 cursor-pointer rounded-md px-2 text-fg-3 hover:text-fg">
            Blank
          </button>
        </div>
        <ScenarioSwitch />
      </div>
      {api.isLive && casesQuery.isError && <p className="rounded-md border border-warn/40 bg-warn-soft px-3 py-2 text-[12.5px] text-warn">The canonical runner case catalog is unavailable: {casesQuery.error.message}</p>}
      {startError && <p role="alert" className="rounded-md border border-warn/40 bg-warn-soft px-3 py-2 text-[12.5px] text-warn">{startError}</p>}

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-lg border border-line bg-surface px-4 py-5 sm:px-6">
          <ol className="grid" aria-label="Campaign steps">
            <Step id="models" index={0} state={stateOf(0)} onEdit={() => go(0)} summary={plan.models.length ? <span className="flex flex-wrap gap-x-3 gap-y-1">{plan.models.map((m) => <ModelChip key={m} id={m} />)}</span> : "Each case's configured default model"}>
              <ModelList history={history} value={plan.models} onChange={(models) => update({ models })} />
              {continueRow(true, plan.models.length ? `Continue with ${plan.models.length} ${plan.models.length === 1 ? "model" : "models"}` : "Continue with case defaults")}
            </Step>
            <Step id="cases" index={1} state={stateOf(1)} onEdit={() => go(1)} summary={plan.cases.length === catalog.length ? `All ${catalog.length} cases` : `${plan.cases.length} of ${catalog.length} cases`}>
              <CasePicker value={plan.cases} onChange={(cases) => update({ cases })} catalog={catalog} disabled={api.isLive && !casesQuery.data} />
              {continueRow(plan.cases.length > 0, "Continue", plan.cases.length ? `${plan.cases.length} selected` : "Select at least one case.")}
            </Step>
            <Step id="technique" index={2} state={stateOf(2)} onEdit={() => go(2)} summary={plan.techniques.map(techniqueLabel).join(", ") || "None selected"}>
              <TechniquePicker history={history} plan={plan} onChange={(techniques) => update({ techniques })} />
              {continueRow(plan.techniques.length > 0)}
            </Step>
            <Step id="repetitions" index={3} state={stateOf(3)} onEdit={() => go(3)} summary={`${plan.repetitions}× · knowledge ${plan.apiModel.trim() || "default"} · verifier ${plan.verificationModel.trim() || "default"}`}>
              <div className="grid gap-5">
                <RepetitionsInput value={plan.repetitions} onChange={(repetitions) => update({ repetitions })} />
                <FixedModels plan={plan} onChange={update} />
              </div>
              {continueRow(errors.length === 0, "Continue to confirm", errors[0])}
            </Step>
            <Step id="confirm" index={4} state={stateOf(4)} onEdit={() => go(4)} summary="">
              <ConfirmStep plan={plan} />
            </Step>
          </ol>
        </div>

        <aside className="hidden xl:sticky xl:top-[72px] xl:block xl:max-h-[calc(100dvh-88px)] xl:overflow-y-auto" aria-label="Plan">
          <PlanRail plan={plan} action={action} onEditPart={(step) => go(STEP_IDS.indexOf(step))} />
        </aside>
      </div>

      <MobileBar plan={plan} action={action} />
    </div>
  );
}
