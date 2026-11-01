import clsx from "clsx";
import { useState } from "react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Panel, Tip } from "@/components/ui";
import { PHASES, type DemoAttempt, type PhaseKey } from "@/demo/campaign";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { StageFallback } from "../OptionsRoom";
import { FailureCallout } from "./GridFirst";
import { JobHeader, LogLine, ModelLabel, StateMark, attemptLook } from "./shared";

// Phase tones form one neutral ramp so the accent can mark only "now".
const PHASE_TONE: Record<PhaseKey, string> = {
  setup: "color-mix(in oklab, var(--fg) 18%, transparent)",
  knowledge: "color-mix(in oklab, var(--fg) 34%, transparent)",
  debug: "color-mix(in oklab, var(--fg) 58%, transparent)",
  verify: "color-mix(in oklab, var(--fg) 34%, transparent)",
  truth: "color-mix(in oklab, var(--fg) 78%, transparent)",
  teardown: "color-mix(in oklab, var(--fg) 18%, transparent)",
};

function Ticks({ total }: { total: number }) {
  const step = total > 3600 ? 900 : 600;
  const ticks = Array.from({ length: Math.floor(total / step) + 1 }, (_, i) => i * step);
  return (
    <div className="relative h-5">
      {ticks.map((tick) => (
        <span key={tick} className="num absolute top-0 -translate-x-1/2 text-[10.5px] text-fg-3" style={{ left: `${(tick / total) * 100}%` }}>
          {clock(tick)}
        </span>
      ))}
    </div>
  );
}

function Bar({ attempt, total, t, selected, onSelect }: { attempt: DemoAttempt; total: number; t: number; selected: boolean; onSelect: () => void }) {
  const { view } = useReplay();
  const state = view?.states[attempt.index] ?? "pending";
  const started = t >= attempt.start;
  return (
    <Tip
      content={
        <div className="grid gap-1">
          <div className="text-fg">
            Attempt {attempt.index + 1} · {humanize(attempt.caseId)}
          </div>
          {attempt.phases.map((p) => (
            <div key={p.key} className="num flex justify-between gap-6">
              <span>{p.label}</span>
              <span>{t >= p.start ? duration(Math.min(t, p.end) - p.start) : `~${duration(p.end - p.start)}`}</span>
            </div>
          ))}
          <div className="text-fg-3">{started ? attemptLook(state).word : "Projected from recorded timings"}</div>
        </div>
      }
    >
      <button
        type="button"
        onClick={onSelect}
        aria-label={`Attempt ${attempt.index + 1}, ${attempt.caseId}: ${attemptLook(state).word}`}
        className={clsx("absolute inset-y-[3px] flex cursor-pointer overflow-hidden rounded-[3px]", selected && "ring-2 ring-fg ring-offset-1 ring-offset-surface")}
        style={{ left: `${(attempt.start / total) * 100}%`, width: `${Math.max(0.4, ((attempt.end - attempt.start) / total) * 100)}%` }}
      >
        {attempt.phases.map((p) => {
          const width = ((p.end - p.start) / (attempt.end - attempt.start)) * 100;
          const running = t >= p.start && t < p.end;
          const reached = t >= p.start;
          const filled = reached ? Math.min(1, (t - p.start) / (p.end - p.start)) : 0;
          return (
            <span key={p.key} className="relative h-full border-r border-surface last:border-r-0" style={{ width: `${width}%` }}>
              <span className="absolute inset-0 border border-dashed border-line-strong" style={{ opacity: reached ? 0 : 1 }} />
              <span className="absolute inset-y-0 left-0" style={{ width: `${filled * 100}%`, background: running ? "var(--accent)" : PHASE_TONE[p.key] }} />
            </span>
          );
        })}
      </button>
    </Tip>
  );
}

// Execution as time: every attempt on one axis, split into its phases, with
// the remaining attempts projected from the replayed run's timings.
export default function CampaignTimeline() {
  const { campaign, view, t } = useReplay();
  const [pinned, setPinned] = useState<number | null>(null);
  if (!campaign || !view) return <StageFallback />;

  const total = campaign.total;
  const latest = view.current?.index ?? Math.max(0, view.done - 1);
  const focus = campaign.attempts[pinned ?? latest];
  const lines = view.events.filter((e) => e.attempt === focus.index).slice(-10);
  const phaseTotals = PHASES.map((meta) => ({
    ...meta,
    seconds: campaign.attempts.reduce((sum, a) => {
      const p = a.phases.find((x) => x.key === meta.key);
      return sum + (p && t >= p.start ? Math.min(t, p.end) - p.start : 0);
    }, 0),
  }));
  const spent = phaseTotals.reduce((sum, p) => sum + p.seconds, 0);

  return (
    <div className="grid gap-4">
      <FailureCallout campaign={campaign} view={view} />
      <section className="rounded-lg border border-line bg-surface p-4">
        <JobHeader />
      </section>

      <section className="overflow-hidden rounded-lg border border-line bg-surface">
        <header className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-line px-4 py-3">
          <h3 className="text-[13.5px] font-medium">Timeline</h3>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-fg-3">
            {PHASES.map((p) => (
              <span key={p.key} className="inline-flex items-center gap-1.5">
                <span className="h-2 w-3 rounded-[2px]" style={{ background: PHASE_TONE[p.key] }} />
                {p.label}
              </span>
            ))}
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-3 rounded-[2px] bg-accent" />
              Now
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-3 rounded-[2px] border border-dashed border-line-strong" />
              Projected
            </span>
          </div>
        </header>
        <div className="overflow-x-auto">
          <div className="min-w-[760px] px-4 pt-3 pb-4">
            <div className="grid grid-cols-[264px_minmax(0,1fr)_64px] gap-3">
              <span />
              <Ticks total={total} />
              <span />
            </div>
            <div className="relative">
              {campaign.attempts.map((attempt) => {
                const state = view.states[attempt.index];
                return (
                  <div key={attempt.index} className="grid grid-cols-[264px_minmax(0,1fr)_64px] items-center gap-3">
                    <div className="flex min-w-0 items-center gap-2 text-[12px]">
                      <span className="num w-5 text-right text-fg-3">{attempt.index + 1}</span>
                      <ModelLabel model={attempt.model} className="w-[124px] shrink-0 text-fg-2" />
                      <VariantCard id={attempt.caseId}>
                        <span tabIndex={0} className={clsx(HINT, "truncate text-fg-3")}>
                          {humanize(attempt.caseId)}
                        </span>
                      </VariantCard>
                    </div>
                    <div className="relative h-6 rounded-[3px] bg-track/60">
                      <Bar attempt={attempt} total={total} t={t} selected={focus.index === attempt.index} onSelect={() => setPinned(attempt.index === latest ? null : attempt.index)} />
                    </div>
                    <span className="flex items-center justify-end gap-1.5 text-[11.5px] text-fg-3">
                      {state !== "pending" && state !== "running" && <StateMark state={state} size={10} />}
                      {state === "running" ? <span className="text-accent">running</span> : state === "pending" ? "" : attemptLook(state).word}
                    </span>
                  </div>
                );
              })}
              <div className="pointer-events-none absolute inset-y-0 grid w-full grid-cols-[264px_minmax(0,1fr)_64px] gap-3" aria-hidden>
                <span />
                <span className="relative">
                  <span className="absolute inset-y-0 w-px bg-accent" style={{ left: `${(t / total) * 100}%` }} />
                </span>
                <span />
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel title="Where the time went" caption={`${duration(spent)} of attempt time so far, by phase`}>
          <div className="grid gap-3">
            <div className="flex h-2.5 overflow-hidden rounded-full bg-track">
              {phaseTotals.map((p) => (
                <span key={p.key} style={{ width: `${spent ? (p.seconds / spent) * 100 : 0}%`, background: PHASE_TONE[p.key] }} />
              ))}
            </div>
            <ul className="grid gap-1.5 text-[12.5px]">
              {phaseTotals.map((p) => (
                <li key={p.key} className="grid grid-cols-[14px_minmax(0,1fr)_auto_48px] items-center gap-2">
                  <span className="h-2 w-3 rounded-[2px]" style={{ background: PHASE_TONE[p.key] }} />
                  <span className="text-fg-2">{p.label}</span>
                  <span className="num text-fg">{duration(p.seconds)}</span>
                  <span className="num text-right text-fg-3">{spent ? Math.round((p.seconds / spent) * 100) : 0}%</span>
                </li>
              ))}
            </ul>
          </div>
        </Panel>
        <Panel
          title={
            <span className="flex flex-wrap items-center gap-2">
              Attempt {focus.index + 1}
              <ModelLabel model={focus.model} className="font-normal" />
            </span>
          }
          caption={pinned !== null ? "Pinned from the timeline" : "Following the live attempt"}
          actions={
            pinned !== null ? (
              <button type="button" onClick={() => setPinned(null)} className="h-7 cursor-pointer rounded-md border border-line-strong px-2.5 text-[12px] text-fg-2 hover:bg-surface-2">
                Back to live
              </button>
            ) : null
          }
        >
          <div className="max-h-[220px] overflow-y-auto">{lines.length ? lines.map((e, i) => <LogLine key={i} event={e} dense />) : <p className="py-6 text-center text-[12.5px] text-fg-3">Not started yet. Projected length {duration(focus.end - focus.start)}.</p>}</div>
        </Panel>
      </div>
    </div>
  );
}
