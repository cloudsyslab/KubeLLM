import clsx from "clsx";
import { Square } from "lucide-react";
import { displayModel } from "@/components/charts";
import { LabLogo } from "@/components/ModelCard";
import { Tip } from "@/components/ui";
import { labOf } from "@/data/models";
import type { AttemptState, DemoAttempt, DemoEvent, DemoPhase, PhaseKey } from "@/demo/campaign";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
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

export type PhaseStatus = "skipped" | "pending" | "current" | "done" | "error" | "pass" | "fail" | "unknown";

// A phase in the grid's vocabulary: the live phase looks like a running cell,
// Ground Truth carries the attempt's outcome, a runner error is amber.
export function phaseStatus(attempt: DemoAttempt, key: PhaseKey, t: number, errorPhase?: PhaseKey): PhaseStatus {
  const phase = attempt.phases.find((p) => p.key === key);
  if (!phase) return "skipped";
  if (t < phase.start) return "pending";
  if (t < phase.end) return key === errorPhase ? "error" : "current";
  if (key === errorPhase) return "error";
  if (key === "truth") return attempt.outcome;
  return "done";
}

export function phaseLook(status: PhaseStatus) {
  switch (status) {
    case "current":
      return { className: "border border-accent bg-accent-soft", word: "Running" };
    case "done":
      return { className: "bg-fg-3", word: "Done" };
    case "skipped":
      return { className: "", word: "Skipped" };
    case "pending":
      return { className: "border border-dashed border-line-strong", word: "Not started" };
    default:
      return attemptLook(status);
  }
}

export function PhaseMark({ status, size = 10 }: { status: PhaseStatus; size?: number }) {
  const look = phaseLook(status);
  return <span aria-hidden className={clsx("inline-block shrink-0 rounded-[2px]", look.className, status === "skipped" && "border border-line")} style={{ width: size, height: size }} />;
}

const SOURCE_LABEL: Record<DemoEvent["source"], string> = {
  runner: "runner",
  kubectl: "kubectl",
  knowledge: "knowledge",
  debug: "debug",
  verifier: "verifier",
  truth: "truth",
};

// Output lines use the grid's colors: Ground Truth checks and verdicts in green
// or red (they carry ✓, ✗, PASS, or FAIL in the text), runner errors and
// warnings in amber, the commands an agent ran in full strength.
const LEVEL_TONE: Record<DemoEvent["level"], string> = {
  info: "text-fg-2",
  command: "text-fg",
  output: "text-fg-3",
  warn: "text-warn",
  error: "text-warn",
  pass: "text-good",
  fail: "text-bad",
};

// The level's mark in the gutter, so a long stream scans like the grid. The
// newest line of a live attempt takes the running accent instead.
const LEVEL_MARK: Partial<Record<DemoEvent["level"], string>> = {
  warn: "bg-warn",
  error: "bg-warn",
  pass: "bg-good",
  fail: "bg-bad",
};

export function LogLine({ event, showAttempt, dense, live }: { event: DemoEvent; showAttempt?: boolean; dense?: boolean; live?: boolean }) {
  const mark = live ? "bg-accent motion-safe:animate-pulse" : LEVEL_MARK[event.level];
  return (
    <div
      className={clsx(
        "relative grid items-baseline gap-x-3 pl-2.5 font-mono text-[11.5px] leading-[1.55]",
        showAttempt ? "grid-cols-[40px_28px_minmax(0,1fr)] sm:grid-cols-[52px_34px_68px_minmax(0,1fr)]" : "grid-cols-[40px_minmax(0,1fr)] sm:grid-cols-[52px_68px_minmax(0,1fr)]",
        dense ? "py-[1px]" : "py-0.5",
      )}
    >
      {mark && <span aria-hidden className={clsx("absolute top-[0.5em] left-0 h-[0.8em] w-[3px] rounded-full", mark)} />}
      <span className="num text-fg-3">{clock(event.t)}</span>
      {showAttempt && <span className="num text-fg-3">#{event.attempt + 1}</span>}
      <span className="hidden truncate text-fg-3 sm:block">{SOURCE_LABEL[event.source]}</span>
      <span className={clsx("break-words", LEVEL_TONE[event.level])}>
        <span className="text-fg-3 sm:hidden">{SOURCE_LABEL[event.source]} </span>
        {event.level === "command" && <span className="text-fg-3 select-none">$ </span>}
        {event.text}
      </span>
    </div>
  );
}

export function phaseOf(attempt: DemoAttempt | undefined, t: number): DemoPhase | undefined {
  return attempt?.phases.find((p) => t >= p.start && t < p.end);
}
