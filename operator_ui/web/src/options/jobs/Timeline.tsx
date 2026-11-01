import clsx from "clsx";
import { Fragment, useMemo, useState, type CSSProperties } from "react";
import { Panel } from "@/components/ui";
import { duration } from "@/lib/format";
import { attemptLook } from "../execution/shared";
import { StageFallback } from "../OptionsRoom";
import { dayOf, dayRange, hm, KIND_LABEL, sessionsOf, shortId, stamp, statusMeta, useJobs, type Job, type Session } from "./model";
import { DemoHistoryTag, JobBody, KIND_ICON, StatusWord } from "./shared";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const STEPS = [MINUTE, 2 * MINUTE, 5 * MINUTE, 10 * MINUTE, 15 * MINUTE, 30 * MINUTE, HOUR, 2 * HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR];

function gapText(ms: number): string {
  const days = ms / (24 * HOUR);
  if (days >= 1) return `${Math.round(days)}d`;
  const hours = ms / HOUR;
  return hours >= 1 ? `${Math.round(hours)}h` : `${Math.round(ms / MINUTE)}m`;
}

/** Wall-clock span of a session; the live one reaches the replay's planned end. */
function domainOf(session: Session): { d0: number; d1: number; plannedEnd?: number } {
  const live = session.jobs.find((job) => job.live && job.status === "running");
  const plannedEnd = live?.campaignData ? live.startMs + live.campaignData.total * 1000 : undefined;
  const start = session.startMs;
  const end = Math.max(session.endMs, plannedEnd ?? 0);
  const pad = Math.max(MINUTE, (end - start) * 0.03);
  return { d0: start - pad, d1: end + pad, plannedEnd };
}

const weight = (session: Session) => 1 + Math.log2(1 + (session.endMs - session.startMs) / HOUR);

function barClass(job: Job): string {
  const tone = statusMeta(job).tone;
  if (tone === "accent") return "border border-accent-line bg-accent-soft";
  if (tone === "warn") return "border border-warn/60 bg-warn-soft";
  if (job.status === "stopped") return "border-r-2 border-fg-2 bg-[var(--bar-muted)]";
  return "bg-[var(--bar-muted)]";
}

function SessionStrip({ sessions, current, onPick }: { sessions: Session[]; current: Session; onPick: (id: string) => void }) {
  return (
    <div className="-mx-1 flex items-stretch overflow-x-auto px-1 pb-1 [scrollbar-width:thin]" role="group" aria-label="Working sessions">
      {sessions.map((session, i) => {
        const { d0, d1 } = domainOf(session);
        const x = (ms: number) => ((ms - d0) / (d1 - d0)) * 100;
        const on = session.id === current.id;
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
              aria-pressed={on}
              onClick={() => onPick(session.id)}
              style={{ flexGrow: weight(session), flexBasis: 0 }}
              className={clsx("min-w-[68px] cursor-pointer rounded-md border px-2 pt-2 pb-1.5 text-left transition-colors", on ? "border-accent-line bg-accent-soft" : "border-line hover:border-line-strong hover:bg-surface-2/60")}
            >
              <span className="relative block h-3" aria-hidden>
                <span className="absolute inset-x-0 top-1/2 h-px bg-line" />
                {session.jobs.map((job) => (
                  <span
                    key={job.id}
                    className={clsx("absolute top-0 h-3 min-w-[3px] rounded-[2px]", statusMeta(job).tone === "accent" ? "bg-accent" : statusMeta(job).tone === "warn" ? "bg-warn" : "bg-fg-3")}
                    style={{ left: `${x(job.startMs)}%`, width: `${Math.max(0, x(job.endMs ?? job.startMs) - x(job.startMs))}%` }}
                  />
                ))}
              </span>
              <span className={clsx("mt-1.5 block truncate text-[12px]", on ? "text-fg" : "text-fg-2")}>
                {session.live && <span className="mr-1 inline-block size-1.5 rounded-full bg-accent align-middle motion-safe:animate-pulse" aria-hidden />}
                {dayRange(session.startMs, session.endMs)}
              </span>
              <span className="num block truncate text-[11px] text-fg-3">
                {session.jobs.length} job{session.jobs.length > 1 ? "s" : ""}
              </span>
            </button>
          </Fragment>
        );
      })}
    </div>
  );
}

function Waterfall({ session, selected, onSelect }: { session: Session; selected: Job; onSelect: (id: string) => void }) {
  const { d0, d1, plannedEnd } = domainOf(session);
  const span = d1 - d0;
  const x = (ms: number) => ((ms - d0) / span) * 100;
  const step = STEPS.find((s) => span / s <= 7) ?? STEPS[STEPS.length - 1];
  const ticks: number[] = [];
  for (let tick = Math.ceil(d0 / step) * step; tick <= d1; tick += step) ticks.push(tick);
  const live = session.jobs.find((job) => job.live && job.status === "running");
  const now = live?.endMs ?? undefined;

  // Occupancy: one job at a time, so busy time is the union of job spans.
  const spans = session.jobs.map((job) => [job.startMs, job.endMs ?? job.startMs] as const).sort((a, b) => a[0] - b[0]);
  const busy = spans.reduce((sum, [a, b]) => sum + (b - a), 0);
  const total = session.endMs - session.startMs;
  const gaps = spans.slice(1).map(([a], i) => ({ from: spans[i][1], to: a })).filter((g) => g.to > g.from);

  const grid = (
    <>
      {ticks.map((tick) => (
        <span key={tick} aria-hidden className="absolute top-0 bottom-0 w-px bg-[var(--grid)]" style={{ left: `${x(tick)}%` }} />
      ))}
      {now !== undefined && <span aria-hidden className="absolute top-0 bottom-0 z-[2] w-px bg-accent" style={{ left: `${x(now)}%` }} />}
    </>
  );

  return (
    <div className="grid gap-1">
      {/* Axis */}
      <div className="grid grid-cols-[108px_minmax(0,1fr)] gap-3 sm:grid-cols-[208px_minmax(0,1fr)]">
        <span className="label self-end !text-[10px]">UTC</span>
        <div className="relative h-5">
          {ticks.map((tick, i) => {
            const midnight = new Date(tick).getUTCHours() === 0 && new Date(tick).getUTCMinutes() === 0;
            return (
              <span
                key={tick}
                className={clsx("num absolute top-0 -translate-x-1/2 text-[11px] whitespace-nowrap", midnight ? "text-fg-2" : "text-fg-3", i % 2 === 1 && "hidden sm:block", now !== undefined && Math.abs(x(tick) - x(now)) < 10 && "invisible")}
                style={{ left: `${x(tick)}%` }}
              >
                {midnight ? dayOf(tick) : hm(tick)}
              </span>
            );
          })}
          {now !== undefined && (
            <span className="absolute top-0 z-[3] -translate-x-1/2 rounded-[3px] bg-accent px-1 font-mono text-[10px] leading-4 font-medium text-accent-ink" style={{ left: `${x(now)}%` }}>
              now
            </span>
          )}
        </div>
      </div>

      {/* Lab occupancy */}
      <div className="grid grid-cols-[108px_minmax(0,1fr)] items-center gap-3 border-b border-line pb-2 sm:grid-cols-[208px_minmax(0,1fr)]">
        <div className="min-w-0">
          <div className="truncate text-[12.5px] text-fg-2">Operator lock</div>
          <div className="num truncate text-[11px] text-fg-3">
            busy {Math.round((busy / Math.max(1, total)) * 100)}% · idle {duration((total - busy) / 1000)}
          </div>
        </div>
        <div className="relative h-6 overflow-hidden rounded-[3px]">
          {grid}
          <span aria-hidden className="hatch absolute inset-y-1 rounded-[2px] opacity-70" style={{ left: `${x(session.startMs)}%`, width: `${x(session.endMs) - x(session.startMs)}%` }} />
          {spans.map(([a, b], i) => (
            <span key={i} aria-hidden className={clsx("absolute inset-y-1 min-w-[2px] rounded-[2px]", live && a === live.startMs ? "bg-accent" : "bg-fg-2")} style={{ left: `${x(a)}%`, width: `${x(b) - x(a)}%` }} />
          ))}
          {plannedEnd !== undefined && now !== undefined && plannedEnd > now && (
            <span aria-hidden className="absolute inset-y-1 rounded-[2px] border border-dashed border-accent-line" style={{ left: `${x(now)}%`, width: `${x(plannedEnd) - x(now)}%` }} />
          )}
          {gaps
            .filter((g) => x(g.to) - x(g.from) > 9)
            .map((g) => (
              <span key={g.from} className="num absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[3px] bg-bg px-1 text-[10.5px] text-fg-3" style={{ left: `${(x(g.from) + x(g.to)) / 2}%` }}>
                {duration((g.to - g.from) / 1000)} idle
              </span>
            ))}
        </div>
      </div>

      {/* One row per job */}
      <ul aria-label={`Jobs on ${dayRange(session.startMs, session.endMs)}`}>
        {session.jobs.map((job) => {
          const Icon = KIND_ICON[job.kind];
          const end = job.endMs ?? job.startMs;
          const left = x(job.startMs);
          const width = Math.max(0, x(end) - left);
          const isLive = plannedEnd !== undefined && job.live && job.status === "running";
          const anchor = isLive ? Math.max(left + width, x(plannedEnd!)) : left + width;
          // Right of the bar when there is room, else left of it, else a chip just past its end.
          const end100 = left + width;
          const place: CSSProperties =
            anchor < 80
              ? { left: `calc(${anchor}% + 6px)` }
              : left > 24
                ? { right: `calc(${100 - left}% + 6px)` }
                : end100 < 70
                  ? { left: `calc(${end100}% + 6px)` }
                  : { right: `calc(${100 - end100}% + 4px)` };
          const chip = anchor >= 80 && left <= 24;
          const on = job.id === selected.id;
          const view = job.view;
          return (
            <li key={job.id}>
              <button
                type="button"
                onClick={() => onSelect(job.id)}
                aria-pressed={on}
                aria-label={`${KIND_LABEL[job.kind]} ${job.title}, ${statusMeta(job).word}, started ${stamp(job.startMs)}, ${duration(job.durationS)}`}
                className={clsx("grid w-full cursor-pointer grid-cols-[108px_minmax(0,1fr)] items-center gap-3 rounded-md text-left transition-colors sm:grid-cols-[208px_minmax(0,1fr)]", on ? "bg-accent-soft" : "hover:bg-surface-2/60")}
              >
                <span className="flex min-w-0 items-center gap-2 py-1.5 pl-2">
                  <Icon className="size-3.5 shrink-0 text-fg-3" strokeWidth={1.75} aria-hidden />
                  <span className="min-w-0">
                    <span className="block truncate text-[12.5px] text-fg">{job.title}</span>
                    <StatusWord job={job} className="!text-[11.5px] sm:hidden" />
                    <span className="hidden items-center gap-2 sm:flex">
                      <StatusWord job={job} className="!text-[11.5px]" />
                      <span className="ident text-[10.5px] text-fg-3">{shortId(job.id)}</span>
                    </span>
                  </span>
                </span>
                <span className="relative block h-11 overflow-hidden">
                  {grid}
                  <span className={clsx("absolute top-1/2 h-4 min-w-[4px] -translate-y-1/2 overflow-hidden rounded-[3px]", barClass(job), on && "outline-2 outline-offset-1 outline-accent")} style={{ left: `${left}%`, width: `${width}%` }} />
                  {view &&
                    job.campaignData?.attempts
                      .filter((a) => view.states[a.index] !== "pending")
                      .map((a) => {
                        const a0 = job.startMs + a.start * 1000;
                        const a1 = job.startMs + Math.min(a.end, view.t) * 1000;
                        return (
                          <span
                            key={a.index}
                            aria-hidden
                            className={clsx("absolute top-1/2 z-[1] h-2.5 -translate-y-1/2 rounded-[1.5px] motion-safe:animate-none", attemptLook(view.states[a.index]).className)}
                            style={{ left: `calc(${x(a0)}% + 1px)`, width: `max(1px, calc(${x(a1) - x(a0)}% - 2px))` }}
                          />
                        );
                      })}
                  {isLive && end < plannedEnd! && (
                    <span aria-hidden className="absolute top-1/2 h-4 -translate-y-1/2 rounded-r-[3px] border border-l-0 border-dashed border-accent-line" style={{ left: `${x(end)}%`, width: `${x(plannedEnd) - x(end)}%` }} />
                  )}
                  <span className={clsx("num absolute top-1/2 z-[3] -translate-y-1/2 text-[11px] whitespace-nowrap text-fg-3", chip && "rounded-[3px] bg-surface px-1")} style={place}>
                    {duration(job.durationS)}
                    {job.total > 0 && job.kind === "campaign" ? ` · ${job.currentIndex}/${job.total}` : ""}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// C: jobs on a time axis. A compressed strip of working sessions (idle days
// collapsed), then the selected session as a waterfall with the operator lock.
export default function Timeline() {
  const { jobs, ready } = useJobs();
  const sessions = useMemo(() => sessionsOf(jobs), [jobs]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  if (!ready || !sessions.length) return <StageFallback />;

  const session = sessions.find((s) => s.id === sessionId) ?? sessions.find((s) => s.live) ?? sessions[sessions.length - 1];
  const selected = session.jobs.find((job) => job.id === selectedId) ?? session.jobs.find((job) => job.live) ?? session.jobs[session.jobs.length - 1];
  const select = (id: string) => {
    const home = sessions.find((s) => s.jobs.some((job) => job.id === id));
    if (home) setSessionId(home.id);
    setSelectedId(id);
  };
  const liveCampaign = session.jobs.find((job) => job.live && job.view);
  const busy = session.jobs.reduce((sum, job) => sum + ((job.endMs ?? job.startMs) - job.startMs), 0);

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 rounded-lg border border-line bg-surface p-4">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <h2 className="text-[13.5px] font-medium">Sessions</h2>
          <span className="text-[12.5px] text-fg-3">Clusters of jobs; idle stretches longer than six hours are collapsed.</span>
          <span className="ml-auto">
            <DemoHistoryTag />
          </span>
        </div>
        <SessionStrip
          sessions={sessions}
          current={session}
          onPick={(id) => {
            setSessionId(id);
            setSelectedId(null);
          }}
        />
      </div>

      <div className="rounded-lg border border-line bg-surface">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-line px-4 py-3">
          <h2 className="text-[13.5px] font-medium">{dayRange(session.startMs, session.endMs)}</h2>
          <span className="num text-[12.5px] text-fg-3">
            {hm(session.startMs)}–{hm(session.endMs)} · {session.jobs.length} job{session.jobs.length > 1 ? "s" : ""} · {duration(busy / 1000)} busy
          </span>
          <span className="ml-auto text-[12px] text-fg-3">One job at a time; bars never overlap.</span>
        </div>
        <div className="px-2 py-3 sm:px-4">
          <Waterfall session={session} selected={selected} onSelect={select} />
        </div>
        {liveCampaign && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-line px-4 py-2 text-[11.5px] text-fg-3">
            <span>Attempts inside the running campaign:</span>
            {(["pass", "fail", "unknown", "running", "error"] as const).map((state) => (
              <span key={state} className="inline-flex items-center gap-1.5">
                <span className={clsx("size-2.5 rounded-[2px] motion-safe:animate-none", attemptLook(state).className)} aria-hidden />
                {attemptLook(state).word}
              </span>
            ))}
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-4 rounded-[2px] border border-dashed border-accent-line" aria-hidden />
              Remaining (estimate)
            </span>
          </div>
        )}
      </div>

      <Panel
        title={
          <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-fg-3">{KIND_LABEL[selected.kind]}</span>
            <span>{selected.title}</span>
            <StatusWord job={selected} />
          </span>
        }
        caption={`${shortId(selected.id)} · started ${stamp(selected.startMs)} · ${duration(selected.durationS)}`}
      >
        <JobBody job={selected} jobs={jobs} onSelect={select} className="lg:grid-cols-2 lg:gap-x-8" />
      </Panel>
    </div>
  );
}
