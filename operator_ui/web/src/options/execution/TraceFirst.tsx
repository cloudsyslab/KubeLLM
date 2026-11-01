import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import type { PhaseKey } from "@/demo/campaign";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { StageFallback } from "../OptionsRoom";
import { FailureCallout } from "./GridFirst";
import { JobHeader, LogLine, ModelLabel, StateMark, attemptLook } from "./shared";

export default function TraceFirst() {
  const { campaign, view, t } = useReplay();
  const [pinnedAttempt, setPinnedAttempt] = useState<number | null>(null);
  const [pinnedPhase, setPinnedPhase] = useState<PhaseKey | null>(null);
  if (!campaign || !view) return <StageFallback />;

  const started = campaign.attempts.filter((a) => t >= a.start);
  const live = view.current?.index ?? Math.max(0, started.length - 1);
  const attempt = campaign.attempts[pinnedAttempt ?? live];
  const span = Math.max(1, attempt.end - attempt.start);
  const livePhase = attempt.phases.find((p) => t >= p.start && t < p.end) ?? [...attempt.phases].reverse().find((p) => t >= p.start);
  const phase = attempt.phases.find((p) => p.key === pinnedPhase && t >= p.start) ?? livePhase ?? attempt.phases[0];
  const phaseEvents = view.events.filter((e) => e.attempt === attempt.index && e.phase === phase.key);

  return (
    <div className="grid gap-4">
      <FailureCallout campaign={campaign} view={view} />
      <section className="rounded-lg border border-line bg-surface p-4">
        <JobHeader />
      </section>
      <section className="grid overflow-hidden rounded-lg border border-line bg-surface lg:grid-cols-[320px_minmax(0,1fr)]">
        <nav aria-label="Attempts" className="max-h-[620px] overflow-y-auto border-b border-line py-1.5 lg:border-r lg:border-b-0">
          <div className="label px-4 pt-1.5 pb-2 !text-[10px]">Trace · {view.planned} attempts</div>
          <ul>
            {campaign.attempts.map((a) => {
              const state = view.states[a.index];
              const selected = a.index === attempt.index;
              const reached = t >= a.start;
              return (
                <li key={a.index}>
                  <button
                    type="button"
                    disabled={!reached}
                    onClick={() => {
                      setPinnedAttempt(a.index === live ? null : a.index);
                      setPinnedPhase(null);
                    }}
                    aria-current={selected || undefined}
                    className={clsx(
                      "grid w-full cursor-pointer grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-2.5 px-4 py-1.5 text-left text-[12.5px] disabled:cursor-default",
                      selected ? "bg-surface-2" : "hover:bg-surface-2/60",
                      !reached && "opacity-50",
                    )}
                  >
                    <StateMark state={state} size={12} />
                    <span className="min-w-0">
                      <span className="flex items-center gap-1.5">
                        <span className="num text-fg-3">{a.index + 1}</span>
                        <ModelLabel model={a.model} className="text-fg" />
                      </span>
                      <span className="block truncate pl-[18px] text-[12px] text-fg-3">{humanize(a.caseId)}</span>
                    </span>
                    <span className="num text-[11.5px] text-fg-3">{reached ? duration(Math.min(t, a.end) - a.start) : ""}</span>
                  </button>
                  {selected && (
                    <ul className="border-l border-line py-0.5 pl-3 ml-[22px]">
                      {a.phases.map((p) => {
                        const on = p.key === phase.key;
                        const reachedPhase = t >= p.start;
                        return (
                          <li key={p.key}>
                            <button
                              type="button"
                              disabled={!reachedPhase}
                              onClick={() => setPinnedPhase(p.key)}
                              className={clsx("flex w-full cursor-pointer items-center gap-2 rounded px-2 py-1 text-left text-[12px] disabled:cursor-default", on ? "text-fg" : "text-fg-3 hover:text-fg", !reachedPhase && "opacity-50")}
                            >
                              <ChevronRight className={clsx("size-3", on ? "text-accent" : "text-transparent")} strokeWidth={2} />
                              {p.label}
                              <span className="num ml-auto">{reachedPhase ? duration(Math.min(t, p.end) - p.start) : "—"}</span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="grid min-w-0 content-start gap-5 p-4">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px]">
            <span className="font-medium">Attempt {attempt.index + 1}</span>
            <span className="text-fg-3">·</span>
            <ModelLabel model={attempt.model} />
            <span className="text-fg-3">·</span>
            <VariantCard id={attempt.caseId}>
              <span tabIndex={0} className={clsx(HINT, "text-fg-2")}>
                {humanize(attempt.caseId)}
              </span>
            </VariantCard>
            <span className="ml-auto text-[12.5px] text-fg-3">{attemptLook(view.states[attempt.index]).word}</span>
          </div>

          <div>
            <div className="label mb-2 !text-[10px]">Waterfall</div>
            <div className="grid gap-1.5">
              {attempt.phases.map((p) => {
                const left = ((p.start - attempt.start) / span) * 100;
                const width = Math.max(0.8, ((Math.min(t, p.end) - p.start) / span) * 100);
                const planned = ((p.end - p.start) / span) * 100;
                const reachedPhase = t >= p.start;
                const current = t >= p.start && t < p.end;
                return (
                  <button
                    key={p.key}
                    type="button"
                    disabled={!reachedPhase}
                    onClick={() => setPinnedPhase(p.key)}
                    className={clsx("grid cursor-pointer grid-cols-[96px_minmax(0,1fr)_64px] items-center gap-3 rounded px-1 py-1 text-left disabled:cursor-default", p.key === phase.key ? "bg-surface-2" : "hover:bg-surface-2/60")}
                  >
                    <span className={clsx("text-[12.5px]", reachedPhase ? "text-fg" : "text-fg-3")}>{p.label}</span>
                    <span className="relative h-3.5">
                      <span className="absolute inset-y-0 rounded-[2px] border border-dashed border-line-strong" style={{ left: `${left}%`, width: `${planned}%` }} />
                      {reachedPhase && <span className={clsx("absolute inset-y-0 rounded-[2px]", current ? "bg-accent" : "bg-fg-3")} style={{ left: `${left}%`, width: `${width}%` }} />}
                    </span>
                    <span className="num text-right text-[12px] text-fg-3">
                      {reachedPhase ? duration(Math.min(t, p.end) - p.start) : "—"}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[12px] text-fg-3">Dashed outlines show each phase's recorded length in the replayed run.</p>
          </div>

          <div className="rounded-md border border-line">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-3 py-2 text-[12.5px]">
              <span className="font-medium">{phase.label}</span>
              <span className="num text-fg-3">{duration(Math.min(t, phase.end) - phase.start)}</span>
              {phase.tokens ? <span className="num text-fg-3">{phase.tokens.toLocaleString()} tokens</span> : null}
              <span className="ml-auto text-fg-3">
                {phaseEvents.length} {phaseEvents.length === 1 ? "line" : "lines"}
              </span>
            </div>
            <div className="max-h-[300px] overflow-y-auto px-3 py-2">
              {phaseEvents.length ? phaseEvents.map((e, i) => <LogLine key={i} event={e} />) : <p className="py-6 text-center text-[12.5px] text-fg-3">No output for this phase yet.</p>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
