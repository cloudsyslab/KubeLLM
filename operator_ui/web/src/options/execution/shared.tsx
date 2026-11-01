import clsx from "clsx";
import { Square } from "lucide-react";
import { displayModel } from "@/components/charts";
import { LabLogo } from "@/components/ModelCard";
import { Tip } from "@/components/ui";
import { labOf } from "@/data/models";
import { PHASES, type AttemptState, type DemoAttempt, type DemoEvent, type DemoPhase } from "@/demo/campaign";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";

export function ModelLabel({ model, className }: { model: string; className?: string }) {
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-1.5", className)}>
      <LabLogo lab={labOf(model)} size={13} />
      <span className="ident truncate">{displayModel(model)}</span>
    </span>
  );
}

export function StatusPill({ status }: { status: "running" | "completed" | "failed" }) {
  const meta = {
    running: { word: "Running", dot: "bg-accent motion-safe:animate-pulse", text: "text-fg" },
    completed: { word: "Completed", dot: "bg-fg-2", text: "text-fg-2" },
    failed: { word: "Stopped on error", dot: "bg-warn", text: "text-warn" },
  }[status];
  return (
    <span className={clsx("inline-flex h-6 items-center gap-1.5 rounded-full border border-line px-2.5 text-[12px] font-medium", meta.text)}>
      <span className={clsx("size-1.5 rounded-full", meta.dot)} aria-hidden />
      {meta.word}
    </span>
  );
}

// Campaign identity, state, determinate progress (a real denominator exists),
// elapsed time, and the connection to the event stream.
export function JobHeader({ compact }: { compact?: boolean }) {
  const { campaign, view, t } = useReplay();
  if (!campaign || !view) return null;
  const remaining = view.status === "running" ? campaign.total - t : 0;
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="min-w-0">
          <div className="label !text-[10px]">Campaign · serial · minh-lane</div>
          <div className="mt-0.5 flex items-center gap-2.5">
            <h2 className="text-[16px] font-medium tracking-[-0.01em]">{campaign.title}</h2>
            <StatusPill status={view.status} />
          </div>
        </div>
        <dl className={clsx("ml-auto flex flex-wrap items-end gap-x-6 gap-y-2", compact && "gap-x-4")}>
          <div>
            <dt className="label !text-[10px]">Attempts</dt>
            <dd className="num mt-0.5 text-[14px] font-medium">
              {view.done} <span className="text-fg-3">/ {view.planned}</span>
            </dd>
          </div>
          <div>
            <dt className="label !text-[10px]">Elapsed</dt>
            <dd className="num mt-0.5 text-[14px] font-medium">{clock(t)}</dd>
          </div>
          {!compact && (
            <div>
              <dt className="label !text-[10px]">Remaining</dt>
              <dd className="num mt-0.5 text-[14px] font-medium text-fg-2">{view.status === "running" ? duration(remaining) : "—"}</dd>
            </div>
          )}
          <div>
            <dt className="label !text-[10px]">Stream</dt>
            <dd className="mt-0.5 flex items-center gap-1.5 text-[13px] text-fg-2">
              <span className="size-1.5 rounded-full bg-fg-2" aria-hidden />
              Connected
            </dd>
          </div>
          <Tip content="Demo replay: stopping is disabled. On the lab, Stop asks the worker to finish the current step and run teardown.">
            <span>
              <button type="button" disabled className="inline-flex h-8 cursor-not-allowed items-center gap-1.5 rounded-md border border-line-strong px-3 text-[12.5px] text-fg-2 opacity-60">
                <Square className="size-3" strokeWidth={2.25} /> Stop
              </button>
            </span>
          </Tip>
        </dl>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-3" role="progressbar" aria-valuenow={view.done} aria-valuemax={view.planned} aria-label="Attempts completed">
        <div className="h-full rounded-full bg-fg-2 transition-[width] duration-300" style={{ width: `${(view.done / view.planned) * 100}%` }} />
      </div>
    </div>
  );
}

export function attemptLook(state: AttemptState) {
  switch (state) {
    case "pass":
      return { className: "bg-good", word: "Pass" };
    case "fail":
      return { className: "border border-bad/70 bg-bad-soft", word: "Fail" };
    case "error":
      return { className: "border border-warn/70 bg-warn-soft", word: "Runner error" };
    case "unknown":
      return { className: "hatch border border-line-strong", word: "Unknown" };
    case "running":
      return { className: "border border-accent bg-accent-soft motion-safe:animate-pulse", word: "Running" };
    default:
      return { className: "border border-dashed border-line-strong", word: "Planned" };
  }
}

export function StateMark({ state, size = 14 }: { state: AttemptState; size?: number }) {
  const look = attemptLook(state);
  return <span aria-label={look.word} className={clsx("inline-block shrink-0 rounded-[3px]", look.className)} style={{ width: size, height: size }} />;
}

const SOURCE_LABEL: Record<DemoEvent["source"], string> = {
  runner: "runner",
  kubectl: "kubectl",
  knowledge: "knowledge",
  debug: "debug",
  verifier: "verifier",
  truth: "truth",
};

export function LogLine({ event, showAttempt, dense }: { event: DemoEvent; showAttempt?: boolean; dense?: boolean }) {
  const tone = {
    info: "text-fg-2",
    command: "text-fg",
    output: "text-fg-3",
    warn: "text-warn",
    error: "text-bad",
    pass: "text-good",
    fail: "text-bad",
  }[event.level];
  return (
    <div className={clsx("grid items-baseline gap-3 font-mono text-[11.5px] leading-[1.55]", showAttempt ? "grid-cols-[52px_34px_72px_minmax(0,1fr)]" : "grid-cols-[52px_72px_minmax(0,1fr)]", dense ? "py-[1px]" : "py-0.5")}>
      <span className="num text-fg-3">{clock(event.t)}</span>
      {showAttempt && <span className="num text-fg-3">#{event.attempt + 1}</span>}
      <span className="truncate text-fg-3">{SOURCE_LABEL[event.source]}</span>
      <span className={clsx("break-words", tone)}>
        {event.level === "command" && <span className="text-fg-3 select-none">$ </span>}
        {event.text}
      </span>
    </div>
  );
}

export function PhaseSteps({ attempt, t }: { attempt: DemoAttempt; t: number }) {
  return (
    <ol className="grid grid-cols-3 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-6">
      {PHASES.map((meta) => {
        const phase = attempt.phases.find((p) => p.key === meta.key);
        const state = !phase ? "skipped" : t >= phase.end ? "done" : t >= phase.start ? "current" : "pending";
        const elapsed = phase ? Math.min(t, phase.end) - phase.start : 0;
        return (
          <li key={meta.key} className={clsx("grid gap-1 bg-surface px-2.5 py-2", state === "current" && "bg-accent-soft")}>
            <div className="flex items-center gap-1.5">
              <span
                aria-hidden
                className={clsx(
                  "size-1.5 rounded-full",
                  state === "done" && "bg-fg-2",
                  state === "current" && "bg-accent motion-safe:animate-pulse",
                  state === "pending" && "border border-fg-3",
                  state === "skipped" && "bg-transparent",
                )}
              />
              <span className={clsx("text-[12px]", state === "current" ? "font-medium text-fg" : state === "done" ? "text-fg-2" : "text-fg-3")}>{meta.label}</span>
            </div>
            <span className="num text-[11.5px] text-fg-3">
              {state === "skipped" ? "skipped" : state === "pending" ? "—" : duration(elapsed)}
              {phase?.tokens && state !== "pending" ? ` · ${(phase.tokens / 1000).toFixed(1)}k tok` : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function caseShort(caseId: string) {
  return humanize(caseId);
}

export function phaseOf(attempt: DemoAttempt | undefined, t: number): DemoPhase | undefined {
  return attempt?.phases.find((p) => t >= p.start && t < p.end);
}
