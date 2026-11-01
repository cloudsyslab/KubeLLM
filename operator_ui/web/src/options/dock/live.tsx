import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";
import { PHASES, viewAt, type AttemptState, type DemoAttempt, type DemoEvent, type DemoPhase } from "@/demo/campaign";
import { JOBS } from "@/demo/jobs";
import { useReplay } from "@/demo/replay";
import { duration } from "@/lib/format";
import { attemptLook } from "../execution/shared";

// Shared state and small pieces for the active-work indicators. The operator
// runs one job at a time (operator_ui/jobs.py), so "active work" is at most
// one job: here, the demo campaign driven by the shared replay.

export type WorkState = "running" | "failed" | "idle";

export interface ActiveWork {
  ready: boolean;
  state: WorkState;
  jobId: string;
  title: string;
  done: number;
  planned: number;
  /** Seconds since the job started (replay clock). */
  elapsed: number;
  /** Mean attempt length times the attempts left; an estimate, not a promise. */
  estimateLeft: number | null;
  current?: DemoAttempt;
  phase?: DemoPhase;
  t: number;
  states: AttemptState[];
  tally: { pass: number; fail: number; unknown: number; error: number };
  /** Finished attempts, newest first. */
  recent: DemoAttempt[];
  lastLine?: DemoEvent;
  errorText?: string;
  failedAttempt?: number;
}

const LIVE_JOB = JOBS.find((job) => job.live) ?? JOBS[0];

export function useActiveWork(force?: "idle"): ActiveWork {
  const { campaign, view, t } = useReplay();
  return useMemo(() => {
    const planned = view?.planned ?? LIVE_JOB.total;
    const base: ActiveWork = {
      ready: Boolean(campaign && view),
      state: "running",
      jobId: LIVE_JOB.id,
      title: campaign?.title ?? LIVE_JOB.title,
      done: 0,
      planned,
      elapsed: 0,
      estimateLeft: null,
      t,
      states: view?.states ?? [],
      tally: { pass: 0, fail: 0, unknown: 0, error: 0 },
      recent: [],
    };
    if (!campaign || !view) return base;
    // A forced idle preview shows the campaign as it would end.
    const final = force === "idle" ? viewAt(campaign, campaign.total) : view;
    const tally = { pass: 0, fail: 0, unknown: 0, error: 0 };
    for (const state of final.states) if (state in tally) tally[state as keyof typeof tally] += 1;
    const finished = campaign.attempts.filter((a) => final.t >= a.end);
    const mean = finished.length ? finished.reduce((sum, a) => sum + (a.end - a.start), 0) / finished.length : null;
    const currentElapsed = view.current ? t - view.current.start : 0;
    const left = view.planned - view.done - (view.current ? 1 : 0);
    const state: WorkState = force === "idle" || view.status === "completed" ? "idle" : view.status === "failed" ? "failed" : "running";
    const error = campaign.events.find((e) => e.level === "error" && e.t <= t);
    return {
      ...base,
      state,
      done: final.done,
      elapsed: force === "idle" ? campaign.total : t,
      estimateLeft: mean !== null && state === "running" ? Math.max(0, mean * left + Math.max(0, mean - currentElapsed)) : null,
      current: state === "running" ? view.current : undefined,
      phase: state === "running" ? view.currentPhase : undefined,
      states: final.states,
      tally,
      recent: [...finished].reverse(),
      lastLine: view.events[view.events.length - 1],
      errorText: error?.text,
      failedAttempt: campaign.failure ? campaign.attempts[campaign.attempts.length - 1]?.index : undefined,
    };
  }, [campaign, view, t, force]);
}

/** True on the Execution page, where the indicators would repeat the page. */
export function useOnExecution(): boolean {
  const { pathname } = useLocation();
  return pathname === "/execution" || pathname.startsWith("/execution/");
}

export function useMediaQuery(query: string): boolean {
  const get = () => (typeof window !== "undefined" && "matchMedia" in window ? window.matchMedia(query).matches : true);
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    if (!("matchMedia" in window)) return;
    const media = window.matchMedia(query);
    const sync = () => setMatches(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, [query]);
  return matches;
}

/**
 * The mobile navigation sheet closes when a nav link is followed; the dock
 * slot does not receive that callback, so a link inside the sheet asks the
 * enclosing Radix dialog to dismiss itself the same way Escape would.
 */
export function closeEnclosingSheet(target: EventTarget | null) {
  if (!(target instanceof Element) || !target.closest('[role="dialog"]')) return;
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
}

export function LiveDot({ state, className }: { state: WorkState; className?: string }) {
  return (
    <span
      aria-hidden
      className={clsx(
        "inline-block size-1.5 shrink-0 rounded-full",
        state === "running" && "bg-accent motion-safe:animate-pulse",
        state === "failed" && "bg-warn",
        state === "idle" && "border border-fg-3",
        className,
      )}
    />
  );
}

export const STATE_WORD: Record<WorkState, string> = { running: "Running", failed: "Stopped on error", idle: "Idle" };

/** One cell per planned attempt. Neutral by default; outcome colors only where a count is shown beside it. */
export function AttemptStrip({ states, outcomes, className, cell = "h-1.5" }: { states: AttemptState[]; outcomes?: boolean; className?: string; cell?: string }) {
  return (
    <div className={clsx("flex gap-[2px]", className)} aria-hidden>
      {states.map((state, i) => (
        <span
          key={i}
          className={clsx(
            "min-w-0 flex-1 rounded-[1.5px]",
            cell,
            outcomes
              ? clsx(attemptLook(state).className, "motion-safe:animate-none")
              : state === "running"
                ? "bg-accent"
                : state === "error"
                  ? "bg-warn"
                  : state === "pending"
                    ? "bg-surface-3"
                    : "bg-fg-2",
          )}
        />
      ))}
    </div>
  );
}

/** The six runner phases of one attempt, the current one accented. */
export function PhaseStrip({ attempt, t, labels = "current", className }: { attempt: DemoAttempt; t: number; labels?: "current" | "all" | "none"; className?: string }) {
  const current = attempt.phases.find((p) => t >= p.start && t < p.end);
  return (
    <div className={clsx("grid gap-1.5", className)}>
      <ol className="grid grid-cols-6 gap-[3px]" aria-label="Attempt phases">
        {PHASES.map((meta) => {
          const phase = attempt.phases.find((p) => p.key === meta.key);
          const state = !phase ? "skipped" : t >= phase.end ? "done" : t >= phase.start ? "current" : "pending";
          return (
            <li key={meta.key} className="grid gap-1" aria-label={`${meta.label}: ${state}`}>
              <span
                className={clsx(
                  "h-1 rounded-full",
                  state === "done" && "bg-fg-2",
                  state === "current" && "bg-accent",
                  state === "pending" && "bg-surface-3",
                  state === "skipped" && "hatch bg-transparent",
                )}
              />
              {labels === "all" && <span className={clsx("hidden truncate text-[10.5px] sm:block", state === "current" ? "text-fg" : "text-fg-3")}>{meta.label}</span>}
            </li>
          );
        })}
      </ol>
      {labels !== "none" && (
        <div className={clsx("flex items-baseline justify-between gap-2 text-[11.5px]", labels === "all" && "sm:hidden")}>
          <span className="text-fg-2">{current ? `${current.label} phase` : "Between phases"}</span>
          <span className="num text-fg-3">{current ? duration(t - current.start) : ""}</span>
        </div>
      )}
    </div>
  );
}

/** Spoken once per attempt, not on every clock tick. */
export function LiveAnnouncer({ work }: { work: ActiveWork }) {
  const text =
    work.state === "running"
      ? `${work.done} of ${work.planned} attempts done${work.current ? `; attempt ${work.current.index + 1} running` : ""}`
      : work.state === "failed"
        ? "Campaign stopped on a runner error"
        : "No active work";
  return (
    <span className="sr-only" aria-live="polite" aria-atomic="true">
      {text}
    </span>
  );
}
