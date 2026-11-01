import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Outcome, Segmented } from "@/components/ui";
import type { DemoAttempt, DemoEvent } from "@/demo/campaign";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { StageFallback } from "../OptionsRoom";
import { FailureCallout } from "./GridFirst";
import { JobHeader, ModelLabel, PhaseSteps, attemptLook } from "./shared";

type Filter = "all" | "pass" | "fail" | "other";

function storyOf(events: DemoEvent[]) {
  const symptom = events.find((e) => e.text.startsWith("fixture ready"))?.text.replace(/^fixture ready · symptom: /, "");
  const plan = events.find((e) => e.source === "knowledge" && e.text.startsWith("plan drafted"))?.text.replace(/^plan drafted: /, "");
  const commands = events
    .filter((e) => e.source === "debug" && e.level === "command")
    .map((e) => e.text.replace(/^kubectl --context \S+ /, "").split(" ").slice(0, 2).join(" "));
  const verifier = events.find((e) => e.text.startsWith("verifier judgment"))?.text.replace(/^verifier judgment: /, "");
  const checks = events.filter((e) => e.source === "truth");
  const error = events.find((e) => e.level === "error");
  const teardown = events.find((e) => e.text.startsWith("teardown verified"));
  return { symptom, plan, commands, verifier, checks, error, teardown };
}

function Line({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[104px_minmax(0,1fr)] sm:gap-3">
      <div className="label pt-0.5 !text-[10px]">{label}</div>
      <div className="text-[13px] leading-relaxed text-fg-2">{children}</div>
    </div>
  );
}

function Story({ attempt, events, live, t }: { attempt: DemoAttempt; events: DemoEvent[]; live: boolean; t: number }) {
  const { view } = useReplay();
  const [open, setOpen] = useState(live);
  const story = storyOf(events);
  const state = view?.states[attempt.index] ?? "pending";
  const elapsed = Math.min(t, attempt.end) - attempt.start;
  const passedChecks = story.checks.filter((c) => c.level === "pass").length;
  const totalChecks = story.checks.filter((c) => c.level === "pass" || c.level === "fail").length;

  return (
    <li className={clsx("overflow-hidden rounded-lg border bg-surface", live ? "border-accent-line" : "border-line")}>
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full cursor-pointer flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-3 text-left hover:bg-surface-2/50">
        <ChevronRight className={clsx("size-3.5 shrink-0 text-fg-3 transition-transform", open && "rotate-90")} strokeWidth={2} />
        <span className="num text-[12px] text-fg-3">#{attempt.index + 1}</span>
        <ModelLabel model={attempt.model} className="text-[13px] text-fg" />
        <span className="text-fg-3">·</span>
        <span className="min-w-0 truncate text-[13px] text-fg-2">{humanize(attempt.caseId)}</span>
        <span className="ml-auto flex items-center gap-3">
          <span className="num text-[12px] text-fg-3">{duration(elapsed)}</span>
          {live ? (
            <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-accent">
              <span className="size-1.5 rounded-full bg-accent motion-safe:animate-pulse" aria-hidden />
              Running
            </span>
          ) : state === "pass" || state === "fail" || state === "unknown" ? (
            <Outcome outcome={state} compact />
          ) : (
            <span className="text-[12px] text-warn">{attemptLook(state).word}</span>
          )}
        </span>
      </button>
      {open && (
        <div className="grid gap-3 border-t border-line px-4 py-4">
          {live && <PhaseSteps attempt={attempt} t={t} />}
          {story.symptom && (
            <Line label="Symptom">
              <VariantCard id={attempt.caseId}>
                <span tabIndex={0} className={clsx(HINT, "text-fg")}>
                  {story.symptom}
                </span>
              </VariantCard>
            </Line>
          )}
          {story.error && <Line label="Runner error">{<span className="text-warn">{story.error.text}</span>}</Line>}
          {story.plan && <Line label="Plan">{story.plan}</Line>}
          {story.commands.length > 0 && (
            <Line label="Agent ran">
              <span className="flex flex-wrap gap-1.5">
                {story.commands.map((command, i) => (
                  <span key={i} className="rounded-[4px] bg-surface-2 px-1.5 py-0.5 font-mono text-[11.5px] text-fg">
                    kubectl {command}
                  </span>
                ))}
              </span>
            </Line>
          )}
          {story.verifier && <Line label="Verifier">Judged the repair {story.verifier}. A separate signal from Ground Truth.</Line>}
          {totalChecks > 0 && (
            <Line label="Ground Truth">
              <span className="grid gap-0.5">
                <span className="text-fg">
                  {passedChecks} of {totalChecks} checks passed
                </span>
                {story.checks
                  .filter((c) => c.level === "fail")
                  .map((c, i) => (
                    <span key={i} className="text-bad">
                      {c.text}
                    </span>
                  ))}
              </span>
            </Line>
          )}
          {story.teardown && <Line label="Teardown">Lane restored to its baseline at {clock(story.teardown.t)}.</Line>}
        </div>
      )}
    </li>
  );
}

// Execution as a story: each attempt reads as symptom, plan, what the agent
// did, the verifier's view, and the Ground Truth verdict.
export default function AttemptStories() {
  const { campaign, view, t } = useReplay();
  const [filter, setFilter] = useState<Filter>("all");
  const byAttempt = useMemo(() => {
    const map = new Map<number, DemoEvent[]>();
    for (const e of view?.events ?? []) map.set(e.attempt, [...(map.get(e.attempt) ?? []), e]);
    return map;
  }, [view?.events]);
  if (!campaign || !view) return <StageFallback />;

  const started = campaign.attempts.filter((a) => t >= a.start).reverse();
  const shown = started.filter((a) => {
    const state = view.states[a.index];
    if (filter === "all" || state === "running") return true;
    if (filter === "other") return state === "unknown" || state === "error";
    return state === filter;
  });
  const counts = {
    pass: view.states.filter((s) => s === "pass").length,
    fail: view.states.filter((s) => s === "fail").length,
    other: view.states.filter((s) => s === "unknown" || s === "error").length,
  };

  return (
    <div className="grid gap-4">
      <FailureCallout campaign={campaign} view={view} />
      <section className="rounded-lg border border-line bg-surface p-4">
        <JobHeader />
      </section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-fg-2">
          {started.length} of {view.planned} attempts started · newest first
        </p>
        <Segmented
          label="Filter attempts"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "All" },
            { value: "pass", label: `Passed ${counts.pass}` },
            { value: "fail", label: `Failed ${counts.fail}` },
            { value: "other", label: `Unknown or error ${counts.other}` },
          ]}
        />
      </div>
      <ol className="grid gap-2">
        {shown.map((attempt) => (
          <Story key={attempt.index} attempt={attempt} events={byAttempt.get(attempt.index) ?? []} live={view.states[attempt.index] === "running"} t={t} />
        ))}
        {!shown.length && <li className="rounded-lg border border-dashed border-line-strong py-10 text-center text-[13px] text-fg-3">No attempts match this filter yet.</li>}
      </ol>
    </div>
  );
}
