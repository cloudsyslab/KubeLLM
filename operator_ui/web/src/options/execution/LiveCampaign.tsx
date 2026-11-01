import clsx from "clsx";
import { useState } from "react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Outcome } from "@/components/ui";
import type { PhaseKey } from "@/demo/campaign";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { runDate } from "@/lib/format";
import { StageFallback } from "../OptionsRoom";
import { AttemptGrid, FailureCallout, GridLegend } from "./grid";
import { JobHeader, ModelLabel } from "./shared";
import { AttemptStory } from "./story";
import { TraceOutput, Waterfall, type OutputScope } from "./trace";

// Execution: the campaign grid fills in live; the attempt box below tells the
// selected attempt's story beside its trace (phase waterfall and output).
export default function LiveCampaign() {
  const { campaign, view, t } = useReplay();
  const [pinned, setPinned] = useState<number | null>(null);
  const [pinnedPhase, setPinnedPhase] = useState<{ attempt: number; key: PhaseKey } | null>(null);
  const [scope, setScope] = useState<OutputScope>("phase");
  const [query, setQuery] = useState("");
  if (!campaign || !view) return <StageFallback />;

  const latest = view.current?.index ?? Math.max(0, view.done - 1);
  const pinnedAttempt = pinned !== null ? campaign.attempts[pinned] : undefined;
  const focus = pinnedAttempt && t >= pinnedAttempt.start ? pinnedAttempt : campaign.attempts[latest];
  const state = view.states[focus.index];
  const events = view.events.filter((e) => e.attempt === focus.index);
  const errorPhase = events.find((e) => e.level === "error")?.phase;

  const livePhase = focus.phases.find((p) => t >= p.start && t < p.end);
  const reached = focus.phases.filter((p) => t >= p.start);
  const defaultPhase =
    livePhase ?? focus.phases.find((p) => p.key === errorPhase) ?? reached.find((p) => p.key === "truth") ?? reached[reached.length - 1] ?? focus.phases[0];
  const chosenPhase = pinnedPhase?.attempt === focus.index ? reached.find((p) => p.key === pinnedPhase.key) : undefined;
  const phase = chosenPhase ?? defaultPhase;

  const onLatest = focus.index === latest;
  const following = onLatest && !chosenPhase;
  const live = onLatest && state === "running";

  const selectAttempt = (index: number) => {
    setPinned(index === latest && view.status === "running" ? null : index);
    setPinnedPhase(null);
  };
  const selectPhase = (key: PhaseKey) => {
    setPinnedPhase(live && key === livePhase?.key ? null : { attempt: focus.index, key });
    setScope("phase");
  };
  const backToLive = () => {
    setPinned(null);
    setPinnedPhase(null);
  };

  return (
    <div className="grid gap-4">
      <FailureCallout campaign={campaign} view={view} />

      <section className="rounded-lg border border-line bg-surface p-4">
        <JobHeader />
        <div className="mt-4">
          <AttemptGrid view={view} selected={focus.index} onSelect={selectAttempt} />
        </div>
        <div className="mt-2">
          <GridLegend />
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label={`Attempt ${focus.index + 1}`}>
        <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <h2 className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[13.5px] leading-5 font-medium">
              <span className="shrink-0">Attempt {focus.index + 1}</span>
              <span className="text-fg-3">·</span>
              <ModelLabel model={focus.model} className="max-w-full font-normal" />
              <span className="text-fg-3">·</span>
              <VariantCard id={focus.caseId}>
                <span tabIndex={0} className={clsx(HINT, "min-w-0 truncate font-normal text-fg-2")}>
                  {humanize(focus.caseId)}
                </span>
              </VariantCard>
            </h2>
            <p className="mt-0.5 text-[12.5px] text-fg-3">
              {!onLatest ? "Pinned. The campaign keeps running." : chosenPhase ? `Showing the ${chosenPhase.label} phase. The attempt keeps running.` : live ? "Following the live attempt" : view.status === "running" ? "Latest attempt" : "Last attempt"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {state === "running" ? (
              <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-accent">
                <span aria-hidden className="size-1.5 rounded-full bg-accent motion-safe:animate-pulse" />
                {livePhase ? `Running · ${livePhase.label}` : "Running"}
              </span>
            ) : state === "error" ? (
              <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-warn">
                <span aria-hidden className="size-[7px] rounded-[2px] border border-warn/70 bg-warn-soft" />
                Runner error
              </span>
            ) : state === "pass" || state === "fail" || state === "unknown" ? (
              <Outcome outcome={state} />
            ) : null}
            {!following && (
              <button type="button" onClick={backToLive} className="h-7 cursor-pointer rounded-md border border-line-strong px-2.5 text-[12px] text-fg-2 hover:bg-surface-2 hover:text-fg">
                Back to live
              </button>
            )}
          </div>
        </header>

        <div className="grid xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="min-w-0 border-b border-line xl:border-r xl:border-b-0">
            <div className="label px-4 pt-3 pb-1 !text-[10px]">Story</div>
            <AttemptStory attempt={focus} events={events} t={t} errorPhase={errorPhase} selected={phase.key} onSelect={selectPhase} />
          </div>
          <div className="grid min-w-0 content-start gap-3 p-4 pt-3">
            <div className="label !text-[10px]">Trace</div>
            <Waterfall attempt={focus} t={t} errorPhase={errorPhase} selected={phase.key} onSelect={selectPhase} />
            <TraceOutput events={view.events} attempt={focus} phase={phase} scope={scope} onScope={setScope} query={query} onQuery={setQuery} live={live} t={t} />
          </div>
        </div>

        <p className="border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
          Outcome and timings replay the recorded run of {runDate(focus.sourceRunId)}. Ground Truth decides the result; the verifier is a separate signal. Commands and output are simulated.
        </p>
      </section>
    </div>
  );
}
