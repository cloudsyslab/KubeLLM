import clsx from "clsx";
import { Fragment } from "react";
import { duration } from "@/lib/format";
import { attemptLook } from "../execution/shared";
import { dayOf, dayRange, hm, statusMeta, type Job, type Session } from "./model";

// Time geometry shared by the session strip, each session's operator lock
// lane, and the per-job span bars, so every bar in a session lines up on one
// axis. One job runs at a time, so spans in a session never overlap.

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const STEPS = [MINUTE, 2 * MINUTE, 5 * MINUTE, 10 * MINUTE, 15 * MINUTE, 30 * MINUTE, HOUR, 2 * HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR];

export function gapText(ms: number): string {
  const days = ms / (24 * HOUR);
  if (days >= 1) return `${Math.round(days)}d`;
  const hours = ms / HOUR;
  return hours >= 1 ? `${Math.round(hours)}h` : `${Math.round(ms / MINUTE)}m`;
}

export interface Domain {
  d0: number;
  d1: number;
  /** Where the running campaign is expected to end. */
  plannedEnd?: number;
  /** The replay clock, while a campaign in this session is running. */
  now?: number;
}

/** Wall-clock span of a session; the live one reaches the replay's planned end. */
export function domainOf(session: Session): Domain {
  const live = session.jobs.find((job) => job.live && job.status === "running");
  const plannedEnd = live?.campaignData ? live.startMs + live.campaignData.total * 1000 : undefined;
  const end = Math.max(session.endMs, plannedEnd ?? 0);
  const pad = Math.max(MINUTE, (end - session.startMs) * 0.03);
  return { d0: session.startMs - pad, d1: end + pad, plannedEnd, now: live?.endMs ?? undefined };
}

export const scaleOf = (domain: Domain) => (ms: number) => ((ms - domain.d0) / (domain.d1 - domain.d0)) * 100;

function ticksOf(domain: Domain): number[] {
  const span = domain.d1 - domain.d0;
  const step = STEPS.find((s) => span / s <= 6) ?? STEPS[STEPS.length - 1];
  const ticks: number[] = [];
  for (let tick = Math.ceil(domain.d0 / step) * step; tick <= domain.d1; tick += step) ticks.push(tick);
  return ticks;
}

/** Busy time on the operator lock: the sum of job spans (they never overlap). */
export function busyMs(jobs: Job[]): number {
  return jobs.reduce((sum, job) => sum + ((job.endMs ?? job.startMs) - job.startMs), 0);
}

export function barClass(job: Job): string {
  const tone = statusMeta(job).tone;
  if (tone === "accent") return "border border-accent-line bg-accent-soft";
  if (tone === "warn") return "border border-warn/60 bg-warn-soft";
  if (job.status === "stopped") return "border-r-2 border-fg-2 bg-[var(--bar-muted)]";
  return "bg-[var(--bar-muted)]";
}

function GridLines({ domain }: { domain: Domain }) {
  const x = scaleOf(domain);
  return (
    <>
      {ticksOf(domain).map((tick) => (
        <span key={tick} aria-hidden className="absolute top-0 bottom-0 w-px bg-[var(--grid)]" style={{ left: `${x(tick)}%` }} />
      ))}
      {domain.now !== undefined && <span aria-hidden className="absolute top-0 bottom-0 z-[2] w-px bg-accent" style={{ left: `${x(domain.now)}%` }} />}
    </>
  );
}

/** Tick labels for a session; midnight ticks name the day. */
export function Axis({ domain }: { domain: Domain }) {
  const x = scaleOf(domain);
  const ticks = ticksOf(domain);
  return (
    <div className="relative h-4" aria-hidden>
      {ticks.map((tick, i) => {
        const date = new Date(tick);
        const midnight = date.getUTCHours() === 0 && date.getUTCMinutes() === 0;
        const nearNow = domain.now !== undefined && Math.abs(x(tick) - x(domain.now)) < 12;
        const nearEdge = x(tick) < 4 || x(tick) > 96;
        return (
          <span
            key={tick}
            className={clsx("num absolute top-0 -translate-x-1/2 text-[10.5px] whitespace-nowrap", midnight ? "text-fg-2" : "text-fg-3", (nearNow || nearEdge) && "invisible", i % 2 === 1 && ticks.length > 4 && "hidden lg:block")}
            style={{ left: `${x(tick)}%` }}
          >
            {midnight ? dayOf(tick) : hm(tick)}
          </span>
        );
      })}
      {domain.now !== undefined && (
        <span className="absolute top-0 z-[3] -translate-x-1/2 rounded-[3px] bg-accent px-1 font-mono text-[10px] leading-4 font-medium text-accent-ink" style={{ left: `${x(domain.now)}%` }}>
          now
        </span>
      )}
    </div>
  );
}

/** The operator lock across a session: busy spans, idle stretches, and the running campaign's remaining estimate. */
export function LockLane({ session, domain }: { session: Session; domain: Domain }) {
  const x = scaleOf(domain);
  const live = session.jobs.find((job) => job.live && job.status === "running");
  const spans = session.jobs.map((job) => ({ job, a: job.startMs, b: job.endMs ?? job.startMs })).sort((p, q) => p.a - q.a);
  const gaps = spans
    .slice(1)
    .map((span, i) => ({ from: spans[i].b, to: span.a }))
    .filter((gap) => gap.to > gap.from);
  return (
    <div className="relative h-6 overflow-hidden rounded-[3px]" aria-hidden>
      <GridLines domain={domain} />
      <span className="hatch absolute inset-y-1 rounded-[2px] opacity-70" style={{ left: `${x(session.startMs)}%`, width: `${x(session.endMs) - x(session.startMs)}%` }} />
      {spans.map(({ job, a, b }) => {
        const tone = statusMeta(job).tone;
        return (
          <span
            key={job.id}
            className={clsx("absolute inset-y-1 min-w-[2px] rounded-[2px]", tone === "accent" ? "bg-accent" : tone === "warn" ? "bg-warn" : "bg-fg-2")}
            style={{ left: `${x(a)}%`, width: `${x(b) - x(a)}%` }}
          />
        );
      })}
      {live && domain.plannedEnd !== undefined && domain.now !== undefined && domain.plannedEnd > domain.now && (
        <span className="absolute inset-y-1 rounded-[2px] border border-dashed border-accent-line" style={{ left: `${x(domain.now)}%`, width: `${x(domain.plannedEnd) - x(domain.now)}%` }} />
      )}
      {gaps
        .filter((gap) => x(gap.to) - x(gap.from) > 12)
        .map((gap) => (
          <span key={gap.from} className="num absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[3px] bg-bg px-1 text-[10.5px] whitespace-nowrap text-fg-3" style={{ left: `${(x(gap.from) + x(gap.to)) / 2}%` }}>
            {duration((gap.to - gap.from) / 1000)} idle
          </span>
        ))}
    </div>
  );
}

/** One job's span on its session's axis; a running campaign shows its attempts inside. */
export function SpanBar({ job, domain, className }: { job: Job; domain: Domain; className?: string }) {
  const x = scaleOf(domain);
  const end = job.endMs ?? job.startMs;
  const left = x(job.startMs);
  const width = Math.max(0, x(end) - left);
  const view = job.view;
  const running = job.live && job.status === "running";
  return (
    <span className={clsx("relative block h-5 overflow-hidden", className)} aria-hidden>
      <GridLines domain={domain} />
      <span className={clsx("absolute top-1/2 h-3.5 min-w-[3px] -translate-y-1/2 rounded-[3px]", barClass(job))} style={{ left: `${left}%`, width: `${width}%` }} />
      {view &&
        job.campaignData?.attempts
          .filter((a) => view.states[a.index] !== "pending")
          .map((a) => {
            const a0 = job.startMs + a.start * 1000;
            const a1 = job.startMs + Math.min(a.end, view.t) * 1000;
            return (
              <span
                key={a.index}
                className={clsx("absolute top-1/2 z-[1] h-2 -translate-y-1/2 rounded-[1.5px] motion-safe:animate-none", attemptLook(view.states[a.index]).className)}
                style={{ left: `calc(${x(a0)}% + 1px)`, width: `max(1px, calc(${x(a1) - x(a0)}% - 2px))` }}
              />
            );
          })}
      {running && domain.plannedEnd !== undefined && end < domain.plannedEnd && (
        <span className="absolute top-1/2 h-3.5 -translate-y-1/2 rounded-r-[3px] border border-l-0 border-dashed border-accent-line" style={{ left: `${x(end)}%`, width: `${x(domain.plannedEnd) - x(end)}%` }} />
      )}
    </span>
  );
}

/** Working sessions with idle stretches collapsed; each button jumps to its session in the feed. */
export function SessionStrip({ sessions, shown, onPick }: { sessions: Session[]; shown: (session: Session) => number; onPick: (session: Session) => void }) {
  return (
    <div className="-mx-1 flex items-stretch overflow-x-auto px-1 pb-1 [scrollbar-width:thin]" role="group" aria-label="Working sessions">
      {sessions.map((session, i) => {
        const domain = domainOf(session);
        const x = scaleOf(domain);
        const count = shown(session);
        const empty = count === 0;
        const range = dayRange(session.startMs, session.endMs);
        return (
          <Fragment key={session.id}>
            {i > 0 && (
              <div className="flex w-7 shrink-0 flex-col items-center justify-center gap-1 sm:w-11" aria-label={`${gapText(session.startMs - sessions[i - 1].endMs)} without jobs`}>
                <span aria-hidden className="h-5 w-px border-l border-dashed border-line-strong" />
                <span className="num text-[10.5px] text-fg-3">{gapText(session.startMs - sessions[i - 1].endMs)}</span>
              </div>
            )}
            <button
              type="button"
              disabled={empty}
              onClick={() => onPick(session)}
              aria-label={`Jump to ${range}, ${count} of ${session.jobs.length} jobs shown`}
              style={{ flexGrow: 1 + Math.log2(1 + (session.endMs - session.startMs) / HOUR), flexBasis: 0 }}
              className={clsx(
                "min-w-[72px] cursor-pointer rounded-md border px-2 pt-2 pb-1.5 text-left transition-colors disabled:cursor-default",
                session.live ? "border-accent-line" : "border-line",
                empty ? "opacity-40" : "hover:border-line-strong hover:bg-surface-2/60",
              )}
            >
              <span className="relative block h-3" aria-hidden>
                <span className="absolute inset-x-0 top-1/2 h-px bg-line" />
                {session.jobs.map((job) => {
                  const tone = statusMeta(job).tone;
                  return (
                    <span
                      key={job.id}
                      className={clsx("absolute top-0 h-3 min-w-[3px] rounded-[2px]", tone === "accent" ? "bg-accent" : tone === "warn" ? "bg-warn" : "bg-fg-3")}
                      style={{ left: `${x(job.startMs)}%`, width: `${Math.max(0, x(job.endMs ?? job.startMs) - x(job.startMs))}%` }}
                    />
                  );
                })}
              </span>
              <span className="mt-1.5 block truncate text-[12px] text-fg-2">
                {session.live && <span className="mr-1 inline-block size-1.5 rounded-full bg-accent align-middle motion-safe:animate-pulse" aria-hidden />}
                {range}
              </span>
              <span className="num block truncate text-[11px] text-fg-3">
                {count === session.jobs.length ? `${session.jobs.length} job${session.jobs.length > 1 ? "s" : ""}` : `${count} of ${session.jobs.length} shown`}
              </span>
            </button>
          </Fragment>
        );
      })}
    </div>
  );
}
