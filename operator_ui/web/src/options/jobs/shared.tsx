import clsx from "clsx";
import { ArrowUpRight, Check, CircleAlert, CornerDownRight, Minus, PackageCheck, Rocket, ShieldCheck, Square, TriangleAlert, Wrench, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router";
import { Outcome, Tag, Tip } from "@/components/ui";
import type { JobKind } from "@/demo/jobs";
import { GROUPS, LANE, summarize, type CheckLevel, type ReadinessCheck } from "@/demo/readiness";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration, runDate } from "@/lib/format";
import { AttemptStrip, PhaseStrip } from "../dock/live";
import { ModelLabel } from "../execution/shared";
import { hms, jobHome, KIND_LABEL, relationsOf, shortId, stamp, statusMeta, timelineOf, useRunIndex, type Job, type Tone } from "./model";

export const KIND_ICON: Record<JobKind, LucideIcon> = {
  readiness: ShieldCheck,
  prepare: Wrench,
  campaign: Rocket,
  publish: PackageCheck,
};

export const TONE_TEXT: Record<Tone, string> = { accent: "text-fg", neutral: "text-fg-2", warn: "text-warn", muted: "text-fg-3" };

export function StatusDot({ tone, className }: { tone: Tone; className?: string }) {
  return (
    <span
      aria-hidden
      className={clsx(
        "inline-block size-1.5 shrink-0 rounded-full",
        tone === "accent" && "bg-accent motion-safe:animate-pulse",
        tone === "neutral" && "bg-fg-2",
        tone === "warn" && "bg-warn",
        tone === "muted" && "border border-fg-3",
        className,
      )}
    />
  );
}

export function StatusWord({ job, className }: { job: Pick<Job, "status" | "kind">; className?: string }) {
  const meta = statusMeta(job);
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-1.5 text-[12.5px] font-medium whitespace-nowrap", TONE_TEXT[meta.tone], className)}>
      <StatusDot tone={meta.tone} />
      {meta.word}
    </span>
  );
}

export function KindLabel({ kind, className, iconClassName }: { kind: JobKind; className?: string; iconClassName?: string }) {
  const Icon = KIND_ICON[kind];
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-1.5 text-fg-2", className)}>
      <Icon className={clsx("size-3.5 shrink-0 text-fg-3", iconClassName)} strokeWidth={1.75} aria-hidden />
      <span className="truncate">{KIND_LABEL[kind]}</span>
    </span>
  );
}

/** Determinate only where a real denominator exists (attempts or checks). */
export function JobProgress({ job, className, bar = "w-14" }: { job: Job; className?: string; bar?: string }) {
  if (!job.total) return <span className={clsx("text-[12px] text-fg-3", className)}>{job.publish ? `${job.publish.files} files` : "—"}</span>;
  const meta = statusMeta(job);
  const share = Math.min(1, job.currentIndex / job.total);
  return (
    <span className={clsx("inline-flex items-center gap-2", className)} role="progressbar" aria-valuenow={job.currentIndex} aria-valuemin={0} aria-valuemax={job.total} aria-label={`${job.currentIndex} of ${job.total} ${job.kind === "campaign" ? "attempts" : "checks"}`}>
      <span className={clsx("h-1 shrink-0 overflow-hidden rounded-full bg-surface-3", bar)}>
        <span
          className={clsx("block h-full rounded-full transition-[width] duration-300", meta.tone === "accent" ? "bg-accent" : meta.tone === "warn" ? "bg-warn" : "bg-fg-2")}
          style={{ width: `${share * 100}%` }}
        />
      </span>
      <span className="num text-[12px] whitespace-nowrap text-fg-2">
        {job.currentIndex}
        <span className="text-fg-3">/{job.total}</span>
      </span>
    </span>
  );
}

export function DemoHistoryTag() {
  return (
    <Tip
      content={
        <div className="grid gap-1">
          <div className="text-fg">Demo job history.</div>
          <div>Kinds, statuses, and labels follow the operator's job store. The running campaign follows the demo replay; completed campaigns link to real recorded runs. Times are UTC.</div>
        </div>
      }
    >
      <span tabIndex={0} className="rounded-[4px]">
        <Tag tone="accent">Demo</Tag>
      </span>
    </Tip>
  );
}

export function SectionLabel({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-2 flex items-center justify-between gap-3">
      <h3 className="label !text-[10px]">{children}</h3>
      {aside}
    </div>
  );
}

export function StopControl({ job, compact }: { job: Job; compact?: boolean }) {
  if (job.kind !== "campaign" || job.status !== "running") return null;
  const why = "Demo replay: Stop is disabled. On the lab, Stop asks the worker to finish the current step, run teardown, and mark the campaign stopped. Completed attempts are kept.";
  return (
    <div className={clsx("flex items-center gap-2", !compact && "flex-wrap")}>
      <Tip content={why}>
        <span tabIndex={0} className="rounded-md">
          <button type="button" disabled aria-label="Stop campaign (disabled in the demo)" className="inline-flex h-7 cursor-not-allowed items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12.5px] text-fg-2 opacity-60">
            <Square className="size-3" strokeWidth={2.25} /> Stop
          </button>
        </span>
      </Tip>
      {!compact && <span className="text-[12px] text-fg-3">Disabled in the demo. On the lab it finishes the current step, then runs teardown.</span>}
    </div>
  );
}

export function HomeLink({ job, className }: { job: Job; className?: string }) {
  const home = jobHome(job);
  return (
    <Link to={home.to} className={clsx("inline-flex h-7 items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12.5px] text-fg hover:bg-surface-2", className)}>
      {home.label} <ArrowUpRight className="size-3.5 text-fg-3" strokeWidth={1.75} />
    </Link>
  );
}

export function RelationChips({ job, jobs, onSelect }: { job: Job; jobs: Job[]; onSelect?: (id: string) => void }) {
  const relations = relationsOf(job, jobs);
  if (!relations.length) return null;
  return (
    <ul className="grid gap-1">
      {relations.map((relation) => (
        <li key={relation.jobId + relation.label}>
          <button
            type="button"
            onClick={() => onSelect?.(relation.jobId)}
            disabled={!onSelect}
            className="inline-flex max-w-full cursor-pointer items-start gap-1.5 rounded-[4px] text-left text-[12.5px] text-fg-2 hover:text-fg disabled:cursor-default"
          >
            <CornerDownRight className="mt-[3px] size-3.5 shrink-0 text-fg-3" strokeWidth={1.75} aria-hidden />
            <span className="min-w-0 underline decoration-line-strong decoration-dotted underline-offset-[3px]">{relation.label}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

// ------------------------------------------------------------------ live

export function LiveNow({ job }: { job: Job }) {
  const { t } = useReplay();
  const view = job.view;
  if (!view || job.status !== "running") return null;
  const current = view.current;
  return (
    <section>
      <SectionLabel aside={<span className="num text-[11.5px] text-fg-3">{job.tally ? `${job.tally.pass} passed · ${job.tally.fail} failed · ${job.tally.unknown} unknown` : ""}</span>}>Now</SectionLabel>
      <div className="grid gap-3 rounded-md border border-accent-line p-3">
        {current ? (
          <>
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
              <span className="font-medium">Attempt {current.index + 1}</span>
              <ModelLabel model={current.model} className="text-fg-2" />
              <span className="text-fg-3">·</span>
              <span className="min-w-0 truncate text-fg-2">{humanize(current.caseId)}</span>
            </div>
            <PhaseStrip attempt={current} t={t} labels="all" />
            <p className="ident truncate text-[11.5px] text-fg-3" title={job.currentLabel}>
              {job.currentLabel}
            </p>
          </>
        ) : (
          <p className="text-[12.5px] text-fg-2">Between attempts.</p>
        )}
        <div className="grid gap-1.5">
          <AttemptStrip states={view.states} outcomes cell="h-2.5" />
          <span className="text-[11.5px] text-fg-3">One cell per planned attempt, in run order.</span>
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------- readiness

function CheckMark({ level }: { level: CheckLevel }) {
  if (level === "pass") return <Check className="size-3.5 shrink-0 text-fg-3" strokeWidth={2} aria-label="Passed" />;
  if (level === "warn") return <TriangleAlert className="size-3.5 shrink-0 text-warn" strokeWidth={2} aria-label="Warning" />;
  if (level === "block") return <CircleAlert className="size-3.5 shrink-0 text-warn" strokeWidth={2} aria-label="Blocking" />;
  return <Minus className="size-3.5 shrink-0 text-fg-3" strokeWidth={2} aria-label="Skipped" />;
}

function CheckRow({ check }: { check: ReadinessCheck }) {
  return (
    <li className="grid grid-cols-[16px_minmax(0,1fr)] gap-x-2 py-1.5">
      <span className="pt-0.5">
        <CheckMark level={check.level} />
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className={clsx("text-[12.5px]", check.group === "live" || check.group === "static" ? "ident" : "", check.level === "pass" ? "text-fg-2" : "text-fg")}>{check.label}</span>
          {check.level !== "pass" && <span className="text-[11.5px] font-medium text-warn">{check.level === "warn" ? "Warning" : check.level === "block" ? "Blocking" : "Skipped"}</span>}
          {check.repairable && check.level !== "pass" && <span className="text-[11.5px] text-fg-3">preparation can repair</span>}
        </div>
        {check.level !== "pass" && <p className="mt-0.5 text-[12px] leading-relaxed text-fg-3">{check.detail}</p>}
      </div>
    </li>
  );
}

export function ReadinessChecks({ checks, mode }: { checks: ReadinessCheck[]; mode: "check-only" | "repair-safe" }) {
  const [all, setAll] = useState(false);
  const s = summarize(checks);
  const flagged = checks.filter((c) => c.level !== "pass");
  return (
    <section>
      <SectionLabel aside={<span className="ident text-[11.5px] text-fg-3">{mode}</span>}>Readiness checks</SectionLabel>
      <div className="grid gap-2">
        <div className="flex gap-[2px]" aria-hidden>
          {checks.map((check) => (
            <span key={check.id} title={check.label} className={clsx("h-2 flex-1 rounded-[1.5px]", check.level === "pass" ? "bg-fg-3/45" : check.level === "skip" ? "bg-surface-3" : "bg-warn")} />
          ))}
        </div>
        <p className="num text-[12.5px] text-fg-2">
          {s.pass} passed
          {s.warn > 0 && <span className="text-warn"> · {s.warn} warning{s.warn > 1 ? "s" : ""}</span>}
          {s.block > 0 && <span className="text-warn"> · {s.block} blocking</span>}
          <span className="text-fg-3"> · {(s.ms / 1000).toFixed(1)}s · lane {LANE.profile}</span>
        </p>
        {flagged.length > 0 && <ul className="divide-y divide-line">{flagged.map((check) => <CheckRow key={check.id} check={check} />)}</ul>}
        <button type="button" onClick={() => setAll(!all)} aria-expanded={all} className="cursor-pointer justify-self-start rounded-[4px] text-[12.5px] text-fg-3 hover:text-fg">
          {all ? "Hide passed checks" : `Show all ${checks.length} checks`}
        </button>
        {all && (
          <div className="grid gap-3">
            {GROUPS.map((group) => {
              const rows = checks.filter((c) => c.group === group.id);
              if (!rows.length) return null;
              return (
                <div key={group.id}>
                  <div className="text-[12px] text-fg-3">{group.label}</div>
                  <ul className="divide-y divide-line">
                    {rows.map((check) => (
                      <CheckRow key={check.id} check={check} />
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ runs

function TruthBar({ passed, known, planned }: { passed: number; known: number; planned: number }) {
  const width = (n: number) => `${(n / Math.max(1, planned)) * 100}%`;
  return (
    <span className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-3" aria-hidden>
      <span className="h-full bg-good" style={{ width: width(passed) }} />
      <span className="h-full bg-bad/80" style={{ width: width(known - passed) }} />
      <span className="hatch h-full" style={{ width: width(planned - known) }} />
    </span>
  );
}

export function CampaignRuns({ job }: { job: Job }) {
  const index = useRunIndex();
  const ids = job.campaign?.runIds ?? [];
  if (job.live && job.campaignData) {
    return (
      <section>
        <SectionLabel>Replay sources</SectionLabel>
        <p className="mb-2 text-[12.5px] text-fg-3">This demo campaign replays the recorded outcomes and timings of these runs. On the lab, each attempt is recorded in the job's run root as it finishes.</p>
        <ul className="divide-y divide-line rounded-md border border-line">
          {job.campaignData.sourceRuns.map((source) => {
            const run = index.get(source.runId);
            const body = (
              <>
                <ModelLabel model={source.model} className="text-[12.5px] text-fg" />
                <span className="num text-[12px] text-fg-3">{runDate(source.runId)}</span>
                {run && <ArrowUpRight className="size-3.5 text-fg-3" strokeWidth={1.75} />}
              </>
            );
            return (
              <li key={source.runId}>
                {run ? (
                  <Link to={`/runs/${run.ref}`} className="grid grid-cols-[minmax(0,1fr)_auto_14px] items-center gap-3 px-3 py-2 hover:bg-surface-2">
                    {body}
                  </Link>
                ) : (
                  <div className="grid grid-cols-[minmax(0,1fr)_auto_14px] items-center gap-3 px-3 py-2">{body}</div>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    );
  }
  if (!ids.length) {
    return (
      <section>
        <SectionLabel>Recorded runs</SectionLabel>
        <p className="text-[12.5px] text-fg-3">
          {job.currentIndex} attempts were recorded in this job's run root as local operator runs. They are not part of the committed snapshot, so there is nothing to link here yet.
        </p>
      </section>
    );
  }
  return (
    <section>
      <SectionLabel aside={<span className="text-[11.5px] text-fg-3">Ground Truth</span>}>Recorded runs</SectionLabel>
      <ul className="divide-y divide-line rounded-md border border-line">
        {ids.map((runId, i) => {
          const run = index.get(runId);
          if (!run) {
            return (
              <li key={runId} className="flex items-center justify-between gap-3 px-3 py-2 text-[12.5px] text-fg-3">
                <span className="num">{runDate(runId)}</span>
                <span>Not in the snapshot</span>
              </li>
            );
          }
          return (
            <li key={runId}>
              <Link to={`/runs/${run.ref}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 px-3 py-2 hover:bg-surface-2 sm:grid-cols-[132px_minmax(0,1fr)_auto_14px]">
                <span className="num text-[12.5px] text-fg">
                  {runDate(runId)} <span className="text-fg-3">· rep {i + 1}</span>
                </span>
                <span className="order-3 col-span-2 sm:order-none sm:col-span-1">
                  <TruthBar passed={run.ground_truth_passed} known={run.ground_truth_known} planned={run.planned_cases} />
                </span>
                <span className="num text-right text-[12px] whitespace-nowrap text-fg-2">
                  {run.ground_truth_passed}/{run.ground_truth_known} passed
                  {run.planned_cases > run.ground_truth_known && <span className="text-fg-3"> · {run.planned_cases - run.ground_truth_known} unknown</span>}
                </span>
                <ArrowUpRight className="hidden size-3.5 text-fg-3 sm:block" strokeWidth={1.75} />
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// --------------------------------------------------------------- publish

export function PublishPack({ job, onSelect }: { job: Job; onSelect?: (id: string) => void }) {
  if (!job.publish) return null;
  const rows: [string, ReactNode][] = [
    ["Pack", <span className="ident break-all">{job.publish.pack}</span>],
    ["Path", <span className="ident break-all">data/exploratory/{job.publish.pack}/</span>],
    ["Files", <span className="num">{job.publish.files}</span>],
    ["Commit", <span>Local commit on <span className="ident">{job.publish.branch}</span>; not pushed</span>],
    [
      "Campaign",
      <button type="button" disabled={!onSelect} onClick={() => onSelect?.(job.publish!.campaignJobId)} className="ident cursor-pointer rounded-[4px] text-fg underline decoration-line-strong decoration-dotted underline-offset-[3px] disabled:cursor-default">
        {shortId(job.publish.campaignJobId)}
      </button>,
    ],
  ];
  return (
    <section>
      <SectionLabel>Published pack</SectionLabel>
      <dl className="grid gap-1.5">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[76px_minmax(0,1fr)] gap-3 text-[12.5px]">
            <dt className="text-fg-3">{label}</dt>
            <dd className="min-w-0 text-fg-2">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// -------------------------------------------------------------- timeline

export function JobTimeline({ job }: { job: Job }) {
  const entries = timelineOf(job);
  return (
    <section>
      <SectionLabel aside={<span className="text-[11.5px] text-fg-3">UTC</span>}>Timeline</SectionLabel>
      <ol className="relative grid gap-0.5 before:absolute before:top-2 before:bottom-2 before:left-[3.5px] before:w-px before:bg-line">
        {entries.map((entry, i) => (
          <li key={i} className="relative grid grid-cols-[8px_minmax(0,1fr)] gap-x-3 py-1">
            <span
              aria-hidden
              className={clsx(
                "relative mt-[6px] size-2 rounded-full border",
                entry.now ? "border-accent bg-accent motion-safe:animate-pulse" : entry.tone === "warn" ? "border-warn bg-warn" : entry.tone === "muted" ? "border-line-strong bg-bg" : "border-fg-3 bg-surface-3",
              )}
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className={clsx("text-[12.5px]", entry.now ? "font-medium text-fg" : TONE_TEXT[entry.tone])}>{entry.text}</span>
                {entry.outcome && <Outcome outcome={entry.outcome} compact />}
                <span className="num ml-auto text-[11.5px] text-fg-3">{hms(entry.atMs)}</span>
              </div>
              {entry.detail && <p className="mt-0.5 text-[12px] leading-relaxed break-words text-fg-3">{entry.detail}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ----------------------------------------------------------------- facts

export function JobFacts({ job }: { job: Job }) {
  const rows: [string, ReactNode][] = [
    ["Job", <span className="ident break-all">{job.id}</span>],
    ["Kind", KIND_LABEL[job.kind]],
    ["Lane", <span className="ident">{LANE.profile}</span>],
    ["Created", stamp(Date.parse(job.createdAt))],
    ["Started", job.startedAt ? stamp(job.startMs) : "—"],
    ["Finished", job.finishedAt ? stamp(Date.parse(job.finishedAt)) : job.status === "running" ? "Running" : "—"],
    ["Duration", <span className="num">{duration(job.durationS)}</span>],
  ];
  if (job.campaign) {
    rows.push(
      ["Models", <span className="grid gap-0.5">{job.campaign.models.map((m) => <ModelLabel key={m} model={m} />)}</span>],
      ["Plan", `${job.campaign.cases} cases × ${job.campaign.repetitions} repetition${job.campaign.repetitions > 1 ? "s" : ""}`],
      ["Technique", <span className="ident">{job.campaign.techniques.join(", ")}</span>],
    );
  }
  return (
    <section>
      <SectionLabel>Details</SectionLabel>
      <dl className="grid gap-1.5">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[76px_minmax(0,1fr)] gap-3 text-[12.5px]">
            <dt className="text-fg-3">{label}</dt>
            <dd className="min-w-0 text-fg-2">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** Everything about one job, in reading order. Used by every Jobs option. */
export function JobBody({ job, jobs, onSelect, className, lead = true, live = true }: { job: Job; jobs: Job[]; onSelect?: (id: string) => void; className?: string; lead?: boolean; live?: boolean }) {
  return (
    <div className={clsx("grid gap-6", className)}>
      <div className="grid gap-3">
        {lead && <p className="text-[13px] leading-relaxed text-fg-2">{job.summary}</p>}
        {lead && job.total > 0 && <JobProgress job={job} bar="flex-1" className="w-full" />}
        {(job.status === "stopped" || job.status === "interrupted") && job.currentLabel && (
          <p className="text-[12px] text-fg-3">
            {job.status === "stopped" ? "Last attempt" : "Interrupted during"} <span className="ident break-all text-fg-2">{job.currentLabel}</span>
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <HomeLink job={job} />
          <StopControl job={job} />
        </div>
        {lead && <RelationChips job={job} jobs={jobs} onSelect={onSelect} />}
      </div>
      {live && <LiveNow job={job} />}
      {job.readiness && <ReadinessChecks checks={job.readiness.checks} mode={job.readiness.mode} />}
      {job.kind === "campaign" && <CampaignRuns job={job} />}
      {job.kind === "publish" && <PublishPack job={job} onSelect={onSelect} />}
      <JobTimeline job={job} />
      <JobFacts job={job} />
    </div>
  );
}

export function Chip({ on, onClick, children, count, label }: { on: boolean; onClick: () => void; children: ReactNode; count?: number; label?: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={label}
      onClick={onClick}
      className={clsx(
        "inline-flex h-7 shrink-0 cursor-pointer items-center gap-1.5 rounded-md border px-2.5 text-[12.5px] transition-colors",
        on ? "border-line-strong bg-surface-3 text-fg" : "border-transparent text-fg-3 hover:bg-surface-2 hover:text-fg",
      )}
    >
      {children}
      {count !== undefined && <span className="num text-[11px] text-fg-3">{count}</span>}
    </button>
  );
}
