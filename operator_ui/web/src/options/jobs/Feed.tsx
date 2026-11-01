import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { PhaseStrip } from "../dock/live";
import { ModelLabel } from "../execution/shared";
import { StageFallback } from "../OptionsRoom";
import { dayKey, dayOf, hm, isToday, KIND_LABEL, KINDS, shortId, stamp, statusMeta, useJobs, weekdayOf, type Job } from "./model";
import { Chip, DemoHistoryTag, JobBody, JobProgress, KIND_ICON, RelationChips, StatusWord, StopControl } from "./shared";

type KindFilter = (typeof KINDS)[number] | "all";

function Node({ job }: { job: Job }) {
  const Icon = KIND_ICON[job.kind];
  const tone = statusMeta(job).tone;
  return (
    <span
      className={clsx(
        "relative z-[1] grid size-7 place-items-center rounded-full border bg-bg",
        tone === "accent" ? "border-accent-line text-accent" : tone === "warn" ? "border-warn/50 text-warn" : "border-line-strong text-fg-3",
      )}
    >
      <Icon className="size-3.5" strokeWidth={1.75} aria-hidden />
    </span>
  );
}

function Entry({ job, jobs, expanded, flash, onToggle, onJump }: { job: Job; jobs: Job[]; expanded: boolean; flash: boolean; onToggle: () => void; onJump: (id: string) => void }) {
  const crossesDay = job.endMs !== null && dayKey(job.endMs) !== dayKey(job.startMs);
  const panel = `feed-detail-${job.id}`;
  return (
    <li id={`feed-${job.id}`} className="group/entry relative grid scroll-mt-28 grid-cols-[28px_minmax(0,1fr)] gap-x-3 sm:grid-cols-[44px_28px_minmax(0,1fr)]">
      <time dateTime={new Date(job.startMs).toISOString()} className="num hidden pt-[5px] text-right text-[12px] text-fg-3 sm:block">
        {hm(job.startMs)}
      </time>
      <div className="relative flex justify-center">
        <span aria-hidden className="absolute top-0 bottom-0 w-px bg-line group-first/entry:top-3.5 group-last/entry:bottom-auto group-last/entry:h-3.5" />
        <Node job={job} />
      </div>
      <div className={clsx("min-w-0 rounded-md pb-6 transition-shadow duration-700", flash && "ring-2 ring-accent-line ring-offset-4 ring-offset-bg")}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 pt-[3px]">
          {job.title !== KIND_LABEL[job.kind] && <span className="text-[12.5px] text-fg-3">{KIND_LABEL[job.kind]}</span>}
          <span className="min-w-0 text-[13.5px] font-medium break-words text-fg">{job.title}</span>
          <StatusWord job={job} />
        </div>
        <p className="mt-0.5 text-[13px] leading-relaxed text-fg-2">{job.summary}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-fg-3">
          <span className="num sm:hidden">{hm(job.startMs)}</span>
          <span className="num">{duration(job.durationS)}</span>
          {crossesDay && job.endMs !== null && <span className="num">ended {stamp(job.endMs)}</span>}
          {job.total > 0 && <JobProgress job={job} />}
          {job.readiness && <span className="ident">{job.readiness.mode}</span>}
          <span className="ident">{shortId(job.id)}</span>
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={expanded}
            aria-controls={panel}
            className="inline-flex h-6 cursor-pointer items-center gap-1 rounded-md px-1.5 text-fg-2 hover:bg-surface-2 hover:text-fg"
          >
            {expanded ? "Hide details" : "Details"}
            <ChevronDown className={clsx("size-3.5 transition-transform", expanded && "rotate-180")} strokeWidth={1.75} />
          </button>
        </div>
        <div className="mt-1.5">
          <RelationChips job={job} jobs={jobs} onSelect={onJump} />
        </div>
        {expanded && (
          <div id={panel} className="mt-3 rounded-md border border-line bg-surface p-4">
            <JobBody job={job} jobs={jobs} onSelect={onJump} lead={false} />
          </div>
        )}
      </div>
    </li>
  );
}

function NowEntry({ job, jobs, expanded, onToggle, onJump }: { job: Job; jobs: Job[]; expanded: boolean; onToggle: () => void; onJump: (id: string) => void }) {
  const { t } = useReplay();
  const current = job.view?.current;
  const panel = `feed-detail-${job.id}`;
  return (
    <section aria-labelledby="feed-now" className="overflow-hidden rounded-lg border border-accent-line bg-surface">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-4 py-2.5">
        <h2 id="feed-now" className="label !text-[10px] !text-accent">
          Now
        </h2>
        <StatusWord job={job} />
        <span className="num text-[12px] text-fg-3">
          started {hm(job.startMs)} · {duration(job.durationS)} elapsed
        </span>
        <span className="ml-auto">
          <DemoHistoryTag />
        </span>
      </header>
      <div className="grid gap-3 px-4 py-3.5">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-[12.5px] text-fg-3">{KIND_LABEL[job.kind]}</span>
          <span className="text-[15px] font-medium tracking-[-0.01em]">{job.title}</span>
        </div>
        <p className="text-[13px] text-fg-2">{job.summary}</p>
        <JobProgress job={job} bar="flex-1" className="w-full" />
        {job.status === "running" && current && (
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] sm:items-center sm:gap-5">
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 text-[12.5px]" aria-live="polite">
              <span className="font-medium">Attempt {current.index + 1}</span>
              <ModelLabel model={current.model} className="text-fg-2" />
              <span className="min-w-0 truncate text-fg-3">{humanize(current.caseId)}</span>
            </div>
            <PhaseStrip attempt={current} t={t} />
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {job.status === "running" && (
            <Link to="/execution" className="inline-flex h-7 items-center rounded-md bg-fg px-2.5 text-[12.5px] font-medium text-bg hover:bg-fg/85">
              Open execution
            </Link>
          )}
          <StopControl job={job} compact />
          <button type="button" onClick={onToggle} aria-expanded={expanded} aria-controls={panel} className="ml-auto inline-flex h-7 cursor-pointer items-center gap-1 rounded-md px-2 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg">
            {expanded ? "Hide details" : "Details"}
            <ChevronDown className={clsx("size-3.5 transition-transform", expanded && "rotate-180")} strokeWidth={1.75} />
          </button>
        </div>
        <RelationChips job={job} jobs={jobs} onSelect={onJump} />
      </div>
      {expanded && (
        <div id={panel} className="border-t border-line px-4 py-4">
          <JobBody job={job} jobs={jobs} onSelect={onJump} lead={false} />
        </div>
      )}
    </section>
  );
}

// B: the job history as a day-grouped story. Related jobs reference each other
// (blocked preflight → preparation → preflight → campaign → publication).
export default function Feed() {
  const { jobs, ready } = useJobs();
  const [open, setOpen] = useState<Set<string>>(() => new Set());
  const [kind, setKind] = useState<KindFilter>("all");
  const [flash, setFlash] = useState<string | null>(null);

  const live = jobs.find((job) => job.live && job.status !== "completed");
  const days = useMemo(() => {
    const rest = jobs.filter((job) => job !== live && (kind === "all" || job.kind === kind)).sort((a, b) => b.startMs - a.startMs);
    const groups: { key: string; ms: number; jobs: Job[] }[] = [];
    for (const job of rest) {
      const key = dayKey(job.startMs);
      const last = groups[groups.length - 1];
      if (last?.key === key) last.jobs.push(job);
      else groups.push({ key, ms: job.startMs, jobs: [job] });
    }
    return groups;
  }, [jobs, live, kind]);

  useEffect(() => {
    if (!flash) return;
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    document.getElementById(`feed-${flash}`)?.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" });
    const id = window.setTimeout(() => setFlash(null), 1600);
    return () => window.clearTimeout(id);
  }, [flash]);

  if (!ready) return <StageFallback />;

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const jump = (id: string) => {
    const target = jobs.find((job) => job.id === id);
    if (target && kind !== "all" && target.kind !== kind) setKind("all");
    setOpen((prev) => new Set(prev).add(id));
    setFlash(id);
  };
  const allIds = jobs.map((job) => job.id);
  const allOpen = allIds.every((id) => open.has(id));

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_220px]">
      <div className="grid min-w-0 content-start gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="-mx-1 flex min-w-0 items-center gap-1 overflow-x-auto px-1 [scrollbar-width:none]" role="group" aria-label="Filter by kind">
            <Chip on={kind === "all"} onClick={() => setKind("all")}>
              Everything
            </Chip>
            {KINDS.map((k) => {
              const Icon = KIND_ICON[k];
              return (
                <Chip key={k} on={kind === k} onClick={() => setKind(k)} count={jobs.filter((job) => job.kind === k).length}>
                  <Icon className="size-3.5" strokeWidth={1.75} aria-hidden /> {KIND_LABEL[k]}
                </Chip>
              );
            })}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button type="button" onClick={() => setOpen(allOpen ? new Set() : new Set(allIds))} className="h-7 cursor-pointer rounded-md px-2 text-[12.5px] text-fg-3 hover:bg-surface-2 hover:text-fg">
              {allOpen ? "Collapse all" : "Expand all"}
            </button>
            {!live && <DemoHistoryTag />}
          </div>
        </div>

        {live && <NowEntry job={live} jobs={jobs} expanded={open.has(live.id)} onToggle={() => toggle(live.id)} onJump={jump} />}

        {days.map((day) => (
          <section key={day.key} id={`feed-day-${day.key}`} aria-label={`${dayOf(day.ms)}`} className="scroll-mt-24">
            <h2 className="sticky top-12 z-10 -mx-1 mb-3 flex items-baseline gap-2 bg-bg/90 px-1 py-1.5 backdrop-blur-md lg:top-14">
              <span className="text-[13px] font-medium text-fg">{isToday(day.ms) ? "Today" : weekdayOf(day.ms)}</span>
              <span className="num text-[12.5px] text-fg-3">{dayOf(day.ms)}</span>
              <span className="num ml-auto text-[11.5px] text-fg-3">
                {day.jobs.length} job{day.jobs.length > 1 ? "s" : ""}
              </span>
            </h2>
            <ol className="grid">
              {day.jobs.map((job) => (
                <Entry key={job.id} job={job} jobs={jobs} expanded={open.has(job.id)} flash={flash === job.id} onToggle={() => toggle(job.id)} onJump={jump} />
              ))}
            </ol>
          </section>
        ))}
        {!days.length && <p className="py-10 text-center text-[13px] text-fg-3">No {kind === "all" ? "" : `${KIND_LABEL[kind].toLowerCase()} `}jobs in this history.</p>}
        <p className="text-[11.5px] text-fg-3">Times in UTC. The operator keeps the latest 30 jobs and runs one at a time.</p>
      </div>

      <nav aria-label="Jump to day" className="hidden xl:block">
        <div className="sticky top-20 grid gap-1">
          <div className="label mb-1 !text-[10px]">Jump to</div>
          {days.map((day) => (
            <a key={day.key} href={`#feed-day-${day.key}`} className="flex items-baseline justify-between gap-3 rounded-md px-2 py-1 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg">
              <span>
                {isToday(day.ms) ? "Today" : dayOf(day.ms)}
                <span className="ml-1.5 text-fg-3">{weekdayOf(day.ms)}</span>
              </span>
              <span className="flex items-center gap-1" aria-label={`${day.jobs.length} jobs`}>
                {day.jobs.map((job) => (
                  <span
                    key={job.id}
                    aria-hidden
                    className={clsx("size-1.5 rounded-full", statusMeta(job).tone === "warn" ? "bg-warn" : statusMeta(job).tone === "accent" ? "bg-accent" : "bg-fg-3")}
                  />
                ))}
              </span>
            </a>
          ))}
        </div>
      </nav>
    </div>
  );
}
