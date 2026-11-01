import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Button, Tag } from "@/components/ui";
import { DEMO_CASES } from "@/demo/campaign";
import { count, duration, usd } from "@/lib/format";
import { LiveAnnouncer, ScenarioSwitch, useFreshness } from "../environment/readiness";
import {
  CATALOG,
  CasePicker,
  EstimateNote,
  FixedModels,
  GateSummary,
  MAX_ATTEMPTS,
  ModelList,
  PreflightButton,
  ReadinessGate,
  RepetitionsInput,
  ReviewDialog,
  TechniquePicker,
  estimate,
  formula,
  plannedCount,
  useHistory,
  validate,
  type Plan,
} from "./plan";

const STARTERS: { id: string; label: string; hint: string; plan: Partial<Plan> }[] = [
  { id: "canonical", label: "Canonical suite", hint: "27 cases · all at once · 5×", plan: { cases: CATALOG, techniques: ["allStepsAtOnce"], repetitions: 5, apiModel: "", verificationModel: "" } },
  { id: "c7e2a91f", label: "Like c7e2a91f", hint: "2 models · 9 cases · 1×", plan: { cases: [...DEMO_CASES], techniques: ["allStepsAtOnce"], models: ["gpt-6-luna", "glm-4.7-flash:latest"], repetitions: 1 } },
];

function Section({ id, title, summary, children, aside }: { id: string; title: string; summary?: ReactNode; children: ReactNode; aside?: ReactNode }) {
  return (
    <section aria-labelledby={id} className="grid gap-3 border-t border-line pt-5 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 id={id} className="text-[14px] font-medium">
          {title}
        </h3>
        <div className="flex items-center gap-3 text-[12.5px] text-fg-3">
          {summary}
          {aside}
        </div>
      </div>
      {children}
    </section>
  );
}

function PlanRail({ plan, onReview }: { plan: Plan; onReview: () => void }) {
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
        <div className="num mt-2 text-[34px] leading-none font-medium tracking-[-0.03em]">{count(total)}</div>
        <ul className="mt-3 grid gap-0.5 font-mono text-[12px] text-fg-2">
          {parts.map((part, i) => (
            <li key={part} className="flex gap-2">
              <span className="w-3 text-fg-3">{i === 0 ? "" : "×"}</span>
              {part}
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
        <Button variant="primary" className="w-full" disabled={errors.length > 0} onClick={onReview}>
          Review {count(total)} {total === 1 ? "attempt" : "attempts"}
        </Button>
      </div>
    </div>
  );
}

function MobileBar({ plan, onReview }: { plan: Plan; onReview: () => void }) {
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
        <Button variant="primary" disabled={validate(plan).length > 0} onClick={onReview}>
          Review
        </Button>
      </div>
    </div>
  );
}

export default function OnePageBuilder() {
  const history = useHistory();
  const [plan, setPlan] = useState<Plan>({ cases: CATALOG, techniques: ["allStepsAtOnce"], models: ["gpt-6-luna"], repetitions: 1, apiModel: "", verificationModel: "" });
  const [review, setReview] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const update = (next: Partial<Plan>) => setPlan((current) => ({ ...current, ...next }));

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
              onClick={() => update(s.plan)}
              className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-line px-2.5 text-fg-2 hover:border-line-strong hover:text-fg"
            >
              {s.label}
              <span className="text-fg-3">{s.hint}</span>
            </button>
          ))}
          <button type="button" onClick={() => setPlan({ cases: [], techniques: ["allStepsAtOnce"], models: [], repetitions: 1, apiModel: "", verificationModel: "" })} className="h-7 cursor-pointer rounded-md px-2 text-fg-3 hover:text-fg">
            Blank
          </button>
        </div>
        <ScenarioSwitch />
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-6 rounded-lg border border-line bg-surface p-4 sm:p-5">
          <Section id="launch-a-models" title="Debug models" summary={plan.models.length ? `${plan.models.length} selected` : "None: each case's default model"}>
            <ModelList history={history} value={plan.models} onChange={(models) => update({ models })} />
          </Section>

          <Section id="launch-a-cases" title="Cases" summary={`${plan.cases.length} of ${CATALOG.length}`}>
            <CasePicker value={plan.cases} onChange={(cases) => update({ cases })} />
          </Section>

          <Section id="launch-a-techniques" title="Technique" summary={`${plan.techniques.length} selected`}>
            <TechniquePicker history={history} plan={plan} onChange={(techniques) => update({ techniques })} />
          </Section>

          <Section id="launch-a-reps" title="Repetitions" summary="Canonical configurations were recorded as 5 runs">
            <RepetitionsInput value={plan.repetitions} onChange={(repetitions) => update({ repetitions })} />
          </Section>

          <section className="border-t border-line pt-4">
            <button type="button" aria-expanded={advanced} onClick={() => setAdvanced(!advanced)} className="flex cursor-pointer items-center gap-1.5 text-[13px] text-fg-2 hover:text-fg">
              <ChevronDown className={clsx("size-3.5 transition-transform", !advanced && "-rotate-90")} strokeWidth={2} />
              Knowledge and verifier models
              <span className="text-fg-3">
                {plan.apiModel.trim() || plan.verificationModel.trim() ? "overridden" : "case defaults"}
              </span>
            </button>
            {advanced && <FixedModels plan={plan} onChange={update} className="mt-3" />}
          </section>
        </div>

        <aside className="hidden xl:sticky xl:top-[72px] xl:block xl:max-h-[calc(100dvh-88px)] xl:overflow-y-auto" aria-label="Plan">
          <PlanRail plan={plan} onReview={() => setReview(true)} />
        </aside>
      </div>

      <MobileBar plan={plan} onReview={() => setReview(true)} />
      <ReviewDialog plan={plan} open={review} onOpenChange={setReview} />
    </div>
  );
}
