import clsx from "clsx";
import { ChevronDown, Search, Timer, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { PhaseStrip } from "../dock/live";
import { ModelLabel } from "../execution/shared";
import { StageFallback } from "../OptionsRoom";
import { dayKey, dayRange, hm, inGroup, isToday, KIND_LABEL, KINDS, sessionsOf, shortId, STATUS_GROUPS, statusMeta, useJobs, weekdayOf, type Job, type Session, type StatusGroup } from "./model";
import { Chip, DemoHistoryTag, JobBody, JobProgress, KIND_ICON, RelationChips, StatusWord, StopControl } from "./shared";
import { Axis, busyMs, domainOf, gapText, LockLane, SessionStrip, SpanBar, type Domain } from "./timing";

type Kind = (typeof KINDS)[number];
type KindFilter = Kind | "all";
const isKind = (value: string | null): value is Kind => KINDS.includes(value as Kind);
const isGroup = (value: string | null): value is StatusGroup => STATUS_GROUPS.some((g) => g.id === value);

// Columns: start time · rail · entry · span on the session's axis (md and up).
const COLS = "grid-cols-[28px_minmax(0,1fr)] sm:grid-cols-[44px_28px_minmax(0,1fr)] md:grid-cols-[44px_28px_minmax(0,1fr)_minmax(200px,34%)]";

function Node({ job }: { job: Job }) {
  const Icon = KIND_ICON[job.kind];
  const tone = statusMeta(job).tone;
  return (
    <span
      className={clsx(
        "relative z-[1] grid size-7 place-items-center rounded-full border",
        tone === "accent" ? "border-accent-line bg-accent-soft text-accent" : tone === "warn" ? "border-warn/50 bg-warn-soft text-warn" : "border-line-strong bg-bg text-fg-3",
      )}
    >
      <Icon className="size-3.5" strokeWidth={1.75} aria-label={KIND_LABEL[job.kind]} />
    </span>
  );
}

function Rail({ first, last, dashed, className, children }: { first?: boolean; last?: boolean; dashed?: boolean; className?: string; children?: ReactNode }) {
  return (
    <div className={clsx("relative flex justify-center", className)}>
      <span
        aria-hidden
        className={clsx("absolute w-px", dashed ? "top-0 bottom-0 border-l border-dashed border-line-strong" : "bg-line", !dashed && (first ? "top-3.5" : "top-0"), !dashed && (last ? "h-3.5" : "bottom-0"))}
      />
      {children}
    </div>
  );
}

/** What the job ran on: models for campaigns, mode for readiness, the pack for publication. */
function Context({ job }: { job: Job }) {
  if (job.campaign) {
    const [first, ...rest] = job.campaign.models;
    return (
      <span className="flex min-w-0 items-center gap-1.5">
        <ModelLabel model={first} className="min-w-0 truncate text-fg-2" />
        {rest.length > 0 && <span className="shrink-0 text-fg-3">+{rest.length}</span>}
      </span>
    );
  }
  if (job.readiness) return <span className="ident truncate">{job.readiness.mode}</span>;
  if (job.publish) return <span className="ident truncate">{job.publish.pack}</span>;
  return null;
}

function SpanCell({ job, domain }: { job: Job; domain: Domain }) {
  const end = job.endMs ?? job.startMs;
  const nextDay = dayKey(end) !== dayKey(job.startMs);
  return (
    <span className="grid gap-0.5">
      <SpanBar job={job} domain={domain} />
      <span className="num text-[10.5px] text-fg-3">
        {hm(job.startMs)}
        {hm(end) !== hm(job.startMs) && `–${hm(end)}`}
        {nextDay && " next day"}
      </span>
    </span>
  );
}

function Entry({ job, jobs, domain, first, last, expanded, flash, onToggle, onJump }: { job: Job; jobs: Job[]; domain: Domain; first: boolean; last: boolean; expanded: boolean; flash: boolean; onToggle: () => void; onJump: (id: string) => void }) {
  const panel = `job-detail-${job.id}`;
  return (
    <li id={`job-${job.id}`} className={clsx("grid scroll-mt-28 gap-x-3", COLS)}>
      <time dateTime={new Date(job.startMs).toISOString()} className="num hidden pt-[5px] text-right text-[12px] text-fg-3 sm:block">
        {hm(job.startMs)}
      </time>
      <Rail first={first} last={last && !expanded} className="row-span-2">
        <Node job={job} />
      </Rail>
      <div className={clsx("min-w-0 rounded-md pb-5 transition-shadow duration-700", flash && "ring-2 ring-accent-line ring-offset-4 ring-offset-bg")}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 pt-[3px]">
          {job.title !== KIND_LABEL[job.kind] && <span className="text-[12.5px] text-fg-3">{KIND_LABEL[job.kind]}</span>}
          <span className="min-w-0 text-[13.5px] font-medium break-words text-fg">{job.title}</span>
          <StatusWord job={job} />
        </div>
        <p className="mt-0.5 text-[13px] leading-relaxed text-fg-2">{job.summary}</p>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[12px] text-fg-3 sm:grid sm:grid-cols-[72px_128px_minmax(0,1fr)_auto]">
          <span className="num inline-flex items-center gap-1 text-fg-2">
            <Timer className="size-3 shrink-0 text-fg-3" strokeWidth={1.75} aria-hidden />
            <span className="sr-only">Duration</span>
            {duration(job.durationS)}
          </span>
          <JobProgress job={job} />
          <span className="flex min-w-0 items-center gap-2">
            <Context job={job} />
            <span className="ident shrink-0 text-fg-3">{shortId(job.id)}</span>
          </span>
          <button
            type="button"
            data-entry-toggle
            onClick={onToggle}
            aria-expanded={expanded}
            aria-controls={panel}
            aria-label={`${expanded ? "Hide" : "Show"} details for ${KIND_LABEL[job.kind].toLowerCase()} ${job.title}`}
            className="inline-flex h-6 cursor-pointer items-center gap-1 justify-self-end rounded-md px-1.5 text-fg-2 hover:bg-surface-2 hover:text-fg"
          >
            {expanded ? "Hide details" : "Details"}
            <ChevronDown className={clsx("size-3.5 transition-transform", expanded && "rotate-180")} strokeWidth={1.75} />
          </button>
        </div>
        <div className="mt-2 md:hidden">
          <SpanCell job={job} domain={domain} />
        </div>
        <div className="mt-1.5">
          <RelationChips job={job} jobs={jobs} onSelect={onJump} />
        </div>
      </div>
      <div className="hidden pt-[5px] md:block">
        <SpanCell job={job} domain={domain} />
      </div>
      {expanded && (
        <div id={panel} className="col-start-2 mb-6 rounded-md border border-line bg-surface p-4 sm:col-start-3 md:col-span-2">
          <JobBody job={job} jobs={jobs} onSelect={onJump} lead={false} className="xl:grid-cols-2 xl:gap-x-8" />
        </div>
      )}
    </li>
  );
}

/** The space between two jobs on the rail: idle time, an overlap, or jobs the filters hide. */
function Between({ text, warn }: { text: string; warn?: boolean }) {
  return (
    <li className={clsx("grid gap-x-3", COLS)}>
      <span className="hidden sm:block" />
      <Rail dashed className="h-6" />
      <span className={clsx("num self-center text-[11px]", warn ? "text-warn" : "text-fg-3")}>{text}</span>
    </li>
  );
}

function betweenText(newer: Job, older: Job, session: Session, shown: Set<string>): { text: string; warn?: boolean } {
  const hidden = session.jobs.filter((job) => !shown.has(job.id) && job.startMs > older.startMs && job.startMs < newer.startMs).length;
  if (hidden) return { text: `${hidden} job${hidden > 1 ? "s" : ""} hidden by filters` };
  const gap = (newer.startMs - (older.endMs ?? older.startMs)) / 1000;
  return gap >= 0 ? { text: `${duration(gap)} idle` } : { text: `Overlaps the previous job by ${duration(-gap)}`, warn: true };
}

function SessionSection({ session, entries, live, liveShown, jobs, open, flash, onToggle, onJump }: { session: Session; entries: Job[]; live?: Job; liveShown: boolean; jobs: Job[]; open: Set<string>; flash: string | null; onToggle: (id: string) => void; onJump: (id: string) => void }) {
  const domain = domainOf(session);
  const busy = busyMs(session.jobs);
  const span = Math.max(1, session.endMs - session.startMs);
  const shown = new Set(entries.map((job) => job.id));
  const liveHere = live && liveShown && session.jobs.includes(live) ? live : undefined;
  if (liveHere) shown.add(liveHere.id);
  const visible = session.jobs.filter((job) => shown.has(job.id)).length;
  const toLive = liveHere && entries[0] ? betweenText(liveHere, entries[0], session, shown) : undefined;
  const label = isToday(session.startMs) ? "Today" : weekdayOf(session.startMs);
  return (
    <section id={`jobs-session-${session.id}`} aria-label={`${label}, ${dayRange(session.startMs, session.endMs)}`} className="scroll-mt-24">
      <h2 className="sticky top-12 z-10 -mx-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 bg-bg/90 px-1 py-1.5 backdrop-blur-md lg:top-14">
        <span className="text-[13px] font-medium text-fg">{label}</span>
        <span className="num text-[12.5px] text-fg-3">
          {dayRange(session.startMs, session.endMs)} · {hm(session.startMs)}–{hm(session.endMs)}
        </span>
        <span className="num ml-auto text-[11.5px] text-fg-3">
          {visible === session.jobs.length ? `${session.jobs.length} job${session.jobs.length > 1 ? "s" : ""}` : `${visible} of ${session.jobs.length} jobs`} · {duration(busy / 1000)} busy
        </span>
      </h2>
      <div className={clsx("mt-1 mb-3 grid items-end gap-x-3 gap-y-1.5", COLS)}>
        <div className="col-start-2 min-w-0 sm:col-start-3">
          <div className="text-[12px] text-fg-2">Operator lock</div>
          <div className="num text-[11px] text-fg-3">
            busy {Math.round((busy / span) * 100)}% · idle {duration((span - busy) / 1000)} · one job at a time
          </div>
        </div>
        <div className="col-start-2 grid min-w-0 gap-0.5 sm:col-start-3 md:col-start-4 md:row-start-1">
          <Axis domain={domain} />
          <LockLane session={session} domain={domain} />
        </div>
      </div>
      <ol className="grid">
        {toLive && <Between text={`${toLive.text}, then the ${liveHere?.status === "running" ? "running" : "latest"} campaign above`} warn={toLive.warn} />}
        {entries.map((job, i) => (
          <EntryWithGap key={job.id} job={job} next={entries[i + 1]} session={session} shown={shown} jobs={jobs} domain={domain} first={i === 0} last={i === entries.length - 1} open={open} flash={flash} onToggle={onToggle} onJump={onJump} />
        ))}
      </ol>
    </section>
  );
}

function EntryWithGap({ job, next, session, shown, jobs, domain, first, last, open, flash, onToggle, onJump }: { job: Job; next?: Job; session: Session; shown: Set<string>; jobs: Job[]; domain: Domain; first: boolean; last: boolean; open: Set<string>; flash: string | null; onToggle: (id: string) => void; onJump: (id: string) => void }) {
  return (
    <>
      <Entry job={job} jobs={jobs} domain={domain} first={first} last={last} expanded={open.has(job.id)} flash={flash === job.id} onToggle={() => onToggle(job.id)} onJump={onJump} />
      {next && <Between {...betweenText(job, next, session, shown)} />}
    </>
  );
}

function NowEntry({ job, jobs, expanded, flash, onToggle, onJump }: { job: Job; jobs: Job[]; expanded: boolean; flash: boolean; onToggle: () => void; onJump: (id: string) => void }) {
  const { t } = useReplay();
  const current = job.view?.current;
  const panel = `job-detail-${job.id}`;
  const running = job.status === "running";
  return (
    <section
      id={`job-${job.id}`}
      aria-labelledby="jobs-now"
      className={clsx("scroll-mt-28 overflow-hidden rounded-lg border bg-surface transition-shadow duration-700", running ? "border-accent-line" : "border-warn/50", flash && "ring-2 ring-accent-line ring-offset-4 ring-offset-bg")}
    >
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-4 py-2.5">
        <h2 id="jobs-now" className={clsx("label !text-[10px]", running ? "!text-accent" : "!text-warn")}>
          {running ? "Now" : "Latest"}
        </h2>
        <StatusWord job={job} />
        <span className="num text-[12px] text-fg-3">
          started {hm(job.startMs)} · {duration(job.durationS)} {running ? "elapsed" : "total"}
        </span>
      </header>
      <div className="grid gap-3 px-4 py-3.5">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-[12.5px] text-fg-3">{KIND_LABEL[job.kind]}</span>
          <span className="text-[15px] font-medium tracking-[-0.01em]">{job.title}</span>
          <span className="ident text-[11.5px] text-fg-3">{shortId(job.id)}</span>
        </div>
        <p className="text-[13px] text-fg-2">{job.summary}</p>
        <JobProgress job={job} bar="flex-1" className="w-full" />
        {running && current && (
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
          <Link to="/execution" className={clsx("inline-flex h-7 items-center rounded-md px-2.5 text-[12.5px] font-medium", running ? "bg-fg text-bg hover:bg-fg/85" : "border border-line-strong text-fg hover:bg-surface-2")}>
            Open execution
          </Link>
          <StopControl job={job} compact />
          <button
            type="button"
            data-entry-toggle
            onClick={onToggle}
            aria-expanded={expanded}
            aria-controls={panel}
            className="ml-auto inline-flex h-7 cursor-pointer items-center gap-1 rounded-md px-2 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg"
          >
            {expanded ? "Hide details" : "Details"}
            <ChevronDown className={clsx("size-3.5 transition-transform", expanded && "rotate-180")} strokeWidth={1.75} />
          </button>
        </div>
        <RelationChips job={job} jobs={jobs} onSelect={onJump} />
      </div>
      {expanded && (
        <div id={panel} className="border-t border-line px-4 py-4">
          <JobBody job={job} jobs={jobs} onSelect={onJump} lead={false} className="xl:grid-cols-2 xl:gap-x-8" />
        </div>
      )}
    </section>
  );
}

// B+C+A: the activity feed, grouped into working sessions. Each session carries
// the operator lock on a time axis and every job's span on that axis; the gaps
// between jobs are stated. The ledger's search, kind, and status filters scope
// everything, and live in the URL.
export default function JobsFeed() {
  const { jobs, ready } = useJobs();
  const [params, setParams] = useSearchParams();
  const kindParam = params.get("kind");
  const statusParam = params.get("status");
  const kind: KindFilter = isKind(kindParam) ? kindParam : "all";
  const group: StatusGroup = isGroup(statusParam) ? statusParam : "all";
  const query = params.get("q") ?? "";
  const target = params.get("job");
  const [open, setOpen] = useState<Set<string>>(() => new Set());
  const [flash, setFlash] = useState<string | null>(null);
  const feed = useRef<HTMLDivElement>(null);

  const patch = (changes: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [key, value] of Object.entries(changes)) {
          if (value === null || value === "" || value === "all") next.delete(key);
          else next.set(key, value);
        }
        return next;
      },
      { replace: true },
    );

  const q = query.trim().toLowerCase();
  const matchesText = (job: Job) => !q || [job.title, job.id, job.summary, KIND_LABEL[job.kind], job.currentLabel ?? "", ...(job.campaign?.models ?? [])].some((text) => text.toLowerCase().includes(q));
  const matches = (job: Job) => (kind === "all" || job.kind === kind) && inGroup(job, group) && matchesText(job);

  const sessions = useMemo(() => sessionsOf(jobs), [jobs]);
  const live = jobs.find((job) => job.live && job.status !== "completed");
  const liveShown = Boolean(live && matches(live));
  const groups = [...sessions]
    .reverse()
    .map((session) => ({ session, entries: session.jobs.filter((job) => job !== live && matches(job)).sort((a, b) => b.startMs - a.startMs) }))
    .filter((g) => g.entries.length > 0);

  // A deep link (?job=) opens that job and brings it into view.
  useEffect(() => {
    if (!ready || !target) return;
    setOpen((prev) => new Set(prev).add(target));
    setFlash(target);
  }, [ready, target]);

  // Jumps scroll instantly: a jump can clear filters and reflow the feed, which
  // throws a smooth scroll off its target. The ring marks where you landed.
  useEffect(() => {
    if (!flash) return;
    document.getElementById(`job-${flash}`)?.scrollIntoView({ block: "start" });
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
    const destination = jobs.find((job) => job.id === id);
    if (destination && !matches(destination)) patch({ kind: null, status: null, q: null });
    setOpen((prev) => new Set(prev).add(id));
    setFlash(id);
  };
  const pickSession = (session: Session) => {
    const el = document.getElementById(`jobs-session-${session.id}`) ?? (live && session.jobs.includes(live) ? document.getElementById(`job-${live.id}`) : null);
    el?.scrollIntoView({ block: "start" });
  };

  const kindCount = (k: KindFilter) => jobs.filter((job) => (k === "all" || job.kind === k) && inGroup(job, group) && matchesText(job)).length;
  const groupCount = (g: StatusGroup) => jobs.filter((job) => (kind === "all" || job.kind === kind) && inGroup(job, g) && matchesText(job)).length;
  const filtered = kind !== "all" || group !== "all" || query !== "";
  const clear = () => patch({ kind: null, status: null, q: null });
  const visibleIds = [...(liveShown && live ? [live.id] : []), ...groups.flatMap((g) => g.entries.map((job) => job.id))];
  const allOpen = visibleIds.length > 0 && visibleIds.every((id) => open.has(id));

  // j and k move between jobs, as in the ledger.
  const onFeedKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey || event.altKey) return;
    const delta = ({ j: 1, k: -1 } as Record<string, number>)[event.key];
    if (!delta || !feed.current) return;
    const toggles = [...feed.current.querySelectorAll<HTMLButtonElement>("[data-entry-toggle]")];
    const at = toggles.indexOf(document.activeElement as HTMLButtonElement);
    const next = toggles[at === -1 ? 0 : Math.max(0, Math.min(toggles.length - 1, at + delta))];
    if (next) {
      event.preventDefault();
      next.focus();
    }
  };

  return (
    <div className="grid gap-5">
      <div className="overflow-hidden rounded-lg border border-line bg-surface">
        <div className="grid gap-2 px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex h-7 min-w-0 flex-1 items-center gap-2 rounded-md bg-surface-2 px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent sm:max-w-[280px]">
              <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
              <input value={query} onChange={(e) => patch({ q: e.target.value })} placeholder="Search jobs, IDs, models" aria-label="Search jobs" className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
              {query && (
                <button type="button" onClick={() => patch({ q: null })} aria-label="Clear search" className="cursor-pointer rounded-[4px] text-fg-3 hover:text-fg">
                  <X className="size-3.5" strokeWidth={1.75} />
                </button>
              )}
            </label>
            <div className="ml-auto flex items-center gap-1">
              {filtered && (
                <button type="button" onClick={clear} className="h-7 cursor-pointer rounded-md px-2 text-[12.5px] text-fg-3 hover:bg-surface-2 hover:text-fg">
                  Clear filters
                </button>
              )}
              <button
                type="button"
                disabled={!visibleIds.length}
                onClick={() => setOpen(allOpen ? new Set() : new Set(visibleIds))}
                className="h-7 cursor-pointer rounded-md px-2 text-[12.5px] text-fg-3 hover:bg-surface-2 hover:text-fg disabled:cursor-default disabled:opacity-40"
              >
                {allOpen ? "Collapse all" : "Expand all"}
              </button>
              <span className="ml-1">
                <DemoHistoryTag />
              </span>
            </div>
          </div>
          <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 [scrollbar-width:none]" role="group" aria-label="Filter by kind">
            <Chip on={kind === "all"} onClick={() => patch({ kind: null })} count={kindCount("all")}>
              All kinds
            </Chip>
            {KINDS.map((k) => {
              const Icon = KIND_ICON[k];
              return (
                <Chip key={k} on={kind === k} onClick={() => patch({ kind: k })} count={kindCount(k)}>
                  <Icon className="size-3.5" strokeWidth={1.75} aria-hidden /> {KIND_LABEL[k]}
                </Chip>
              );
            })}
          </div>
          <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 [scrollbar-width:none]" role="group" aria-label="Filter by status">
            {STATUS_GROUPS.map((g) => (
              <Chip key={g.id} on={group === g.id} onClick={() => patch({ status: g.id })} count={groupCount(g.id)}>
                {g.id === "attention" && <span className="size-1.5 rounded-full bg-warn" aria-hidden />}
                {g.id === "active" && <span className="size-1.5 rounded-full bg-accent" aria-hidden />}
                {g.id === "all" ? "Any status" : g.label}
              </Chip>
            ))}
          </div>
        </div>
        <div className="grid gap-2 border-t border-line px-3 py-2.5">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <h2 className="text-[12.5px] font-medium">Sessions</h2>
            <span className="text-[12px] text-fg-3">Clusters of jobs; idle stretches longer than six hours are collapsed. Select one to jump to it.</span>
          </div>
          <SessionStrip sessions={sessions} shown={(session) => session.jobs.filter(matches).length} onPick={pickSession} />
        </div>
      </div>

      <div ref={feed} onKeyDown={onFeedKey} className="grid gap-5">
        {live && liveShown && <NowEntry job={live} jobs={jobs} expanded={open.has(live.id)} flash={flash === live.id} onToggle={() => toggle(live.id)} onJump={jump} />}

        {groups.map((g, i) => (
          <div key={g.session.id} className="grid gap-5">
            {i > 0 && (
              <div role="separator" className="flex items-center gap-3 text-[11.5px] text-fg-3">
                <span aria-hidden className="h-px flex-1 border-t border-dashed border-line-strong" />
                <span className="num">{gapText(groups[i - 1].session.startMs - g.session.endMs)} without jobs</span>
                <span aria-hidden className="h-px flex-1 border-t border-dashed border-line-strong" />
              </div>
            )}
            <SessionSection session={g.session} entries={g.entries} live={live} liveShown={liveShown} jobs={jobs} open={open} flash={flash} onToggle={toggle} onJump={jump} />
          </div>
        ))}

        {!groups.length && !liveShown && (
          <div className="grid place-items-center gap-2 rounded-lg border border-line px-4 py-12 text-center">
            <p className="text-[13px] text-fg-2">No jobs match these filters.</p>
            <button type="button" onClick={clear} className="h-7 cursor-pointer rounded-md border border-line-strong px-2.5 text-[12.5px] text-fg hover:bg-surface-2">
              Clear filters
            </button>
          </div>
        )}
      </div>

      <p className="text-[11.5px] text-fg-3">
        Times in UTC. The operator keeps the latest 30 jobs and runs one at a time. <kbd className="font-mono">j</kbd> / <kbd className="font-mono">k</kbd> move between jobs.
      </p>
    </div>
  );
}
