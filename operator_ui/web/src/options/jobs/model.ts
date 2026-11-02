import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "@/api/client";
import type { Run } from "@/api/types";
import { displayModel } from "@/components/charts";
import { FAILURE_ATTEMPT, type AttemptState, type CampaignView, type DemoCampaign } from "@/demo/campaign";
import { DEMO_NOW, JOBS, KIND_LABEL, PUBLISH_PREVIEW, type DemoJob, type JobKind, type JobStatus } from "@/demo/jobs";
import { READINESS_TTL_MIN, summarize } from "@/demo/readiness";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";

// Job history for the Jobs options. Kinds, statuses, labels, and the
// one-job-at-a-time lock mirror operator_ui/jobs.py and worker.py. The live
// campaign takes its status and progress from the shared demo replay.

export const NOW_MS = Date.parse(DEMO_NOW);

export interface Tally {
  pass: number;
  fail: number;
  unknown: number;
  error: number;
}

export interface Job extends DemoJob {
  startMs: number;
  /** Finish time, or "now" on the replay clock for the live job. */
  endMs: number | null;
  durationS: number | null;
  /** Replay state while this is the live campaign. */
  view?: CampaignView;
  campaignData?: DemoCampaign;
  tally?: Tally;
}

export function tallyOf(states: AttemptState[]): Tally {
  const tally: Tally = { pass: 0, fail: 0, unknown: 0, error: 0 };
  for (const state of states) {
    if (state === "pass" || state === "fail" || state === "unknown" || state === "error") tally[state] += 1;
  }
  return tally;
}

function staticJob(job: DemoJob): Job {
  const startMs = Date.parse(job.startedAt ?? job.createdAt);
  const endMs = job.finishedAt ? Date.parse(job.finishedAt) : null;
  return { ...job, startMs, endMs, durationS: endMs === null ? null : (endMs - startMs) / 1000 };
}

/** Mirrors the worker's current_label: case · technique · model · repetition. */
export const attemptLabel = (caseId: string, model: string) => `${caseId} · allStepsAtOnce · ${model} · repetition 1`;

function liveJob(job: DemoJob, campaign: DemoCampaign | undefined, view: CampaignView | undefined, t: number): Job {
  const base = staticJob(job);
  if (!campaign || !view) return { ...base, endMs: null, durationS: null };
  const status: JobStatus = view.status === "running" ? "running" : view.status === "completed" ? "completed" : "failed";
  const tally = tallyOf(view.states);
  const endMs = base.startMs + t * 1000;
  const notStarted = view.planned - campaign.attempts.length;
  const summary =
    status === "running"
      ? `${view.done} of ${view.planned} attempts · ${tally.pass} passed Ground Truth so far`
      : status === "completed"
        ? `${view.done} attempts recorded · ${tally.pass} passed Ground Truth`
        : `Runner error in attempt ${FAILURE_ATTEMPT + 1}; teardown completed · ${notStarted} planned attempts not started`;
  return {
    ...base,
    status,
    total: view.planned,
    currentIndex: view.done,
    currentLabel: view.current ? attemptLabel(view.current.caseId, view.current.model) : status === "running" ? "Preparing serial campaign." : undefined,
    finishedAt: status === "running" ? undefined : new Date(endMs).toISOString(),
    endMs,
    durationS: t,
    summary,
    view,
    campaignData: campaign,
    tally,
  };
}

export function resolveJobs(campaign: DemoCampaign | undefined, view: CampaignView | undefined, t: number): Job[] {
  return JOBS.map((job) => (job.live ? liveJob(job, campaign, view, t) : staticJob(job)));
}

/** Every job with the live campaign merged from the replay, newest first. */
export function useJobs(): { jobs: Job[]; ready: boolean } {
  const { campaign, view, t } = useReplay();
  const jobs = useMemo(() => resolveJobs(campaign, view, t), [campaign, view, t]);
  return { jobs, ready: Boolean(campaign) };
}

// ---------------------------------------------------------------- statuses

export type Tone = "accent" | "neutral" | "warn" | "muted";

export function statusMeta(job: Pick<Job, "status" | "kind">): { word: string; tone: Tone } {
  switch (job.status) {
    case "running":
      return { word: "Running", tone: "accent" };
    case "queued":
      return { word: "Queued", tone: "muted" };
    case "completed":
      return { word: job.kind === "readiness" || job.kind === "prepare" ? "Ready" : "Completed", tone: "neutral" };
    case "failed":
      return { word: job.kind === "campaign" ? "Stopped on error" : "Failed", tone: "warn" };
    case "stopped":
      return { word: "Stopped", tone: "neutral" };
    case "interrupted":
      return { word: "Interrupted", tone: "warn" };
    case "blocked":
      return { word: "Blocked", tone: "warn" };
  }
}

export type StatusGroup = "all" | "active" | "attention" | "done" | "stopped";
export const STATUS_GROUPS: { id: StatusGroup; label: string; hint: string }[] = [
  { id: "all", label: "All", hint: "Every job" },
  { id: "active", label: "Active", hint: "Queued or running" },
  { id: "attention", label: "Needs attention", hint: "Failed, blocked, or interrupted" },
  { id: "done", label: "Completed", hint: "Finished normally" },
  { id: "stopped", label: "Stopped", hint: "Stopped by the operator" },
];

export function inGroup(job: Job, group: StatusGroup): boolean {
  switch (group) {
    case "all":
      return true;
    case "active":
      return job.status === "running" || job.status === "queued";
    case "attention":
      return job.status === "failed" || job.status === "blocked" || job.status === "interrupted";
    case "done":
      return job.status === "completed";
    case "stopped":
      return job.status === "stopped";
  }
}

export const KINDS: JobKind[] = ["readiness", "prepare", "campaign", "publish"];
export { KIND_LABEL };

/** The page that owns each kind of job. */
export function jobHome(job: Job): { to: string; label: string } {
  if (job.kind === "campaign") return job.status === "running" || job.live ? { to: "/execution", label: "Open execution" } : { to: "/runs", label: "Open runs" };
  if (job.kind === "publish") return { to: "/publish", label: "Open publish" };
  return { to: "/environment", label: "Open environment" };
}

// ------------------------------------------------------------------ time

const DAY = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const WEEKDAY = new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: "UTC" });
const HM = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" });
const HMS = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "UTC" });

export const dayOf = (ms: number) => DAY.format(ms);
export const weekdayOf = (ms: number) => WEEKDAY.format(ms);
export const hm = (ms: number) => HM.format(ms);
export const hms = (ms: number) => HMS.format(ms);
/** "Nov 1 · 19:12", the same shape as run dates elsewhere. */
export const stamp = (ms: number) => `${DAY.format(ms)} · ${HM.format(ms)}`;
export const dayKey = (ms: number) => new Date(ms).toISOString().slice(0, 10);
export const isToday = (ms: number) => dayKey(ms) === dayKey(NOW_MS);
export const shortId = (id: string) => id.slice(0, 8);

// ------------------------------------------------------------- relations

export interface Relation {
  label: string;
  jobId: string;
}

const byStart = (jobs: Job[]) => [...jobs].sort((a, b) => a.startMs - b.startMs);

/** The completed preflight that gated a campaign (fresh for 20 minutes). */
export function gateOf(job: Job, jobs: Job[]): { job: Job; ageS: number } | undefined {
  if (job.kind !== "campaign") return undefined;
  const candidates = jobs.filter((other) => (other.kind === "readiness" || other.kind === "prepare") && other.status === "completed" && other.endMs !== null && other.endMs <= job.startMs);
  const gate = candidates.sort((a, b) => (b.endMs ?? 0) - (a.endMs ?? 0))[0];
  if (!gate || gate.endMs === null) return undefined;
  const ageS = (job.startMs - gate.endMs) / 1000;
  return ageS <= READINESS_TTL_MIN * 60 ? { job: gate, ageS } : undefined;
}

export function relationsOf(job: Job, jobs: Job[]): Relation[] {
  const ordered = byStart(jobs);
  const index = ordered.findIndex((j) => j.id === job.id);
  const next = ordered[index + 1];
  const prev = ordered[index - 1];
  const out: Relation[] = [];
  if (job.kind === "readiness" && job.status === "blocked" && next?.kind === "prepare") out.push({ label: `Followed by preparation ${shortId(next.id)}`, jobId: next.id });
  if (job.kind === "prepare" && prev?.kind === "readiness" && prev.status === "blocked") out.push({ label: `After blocked preflight ${shortId(prev.id)}`, jobId: prev.id });
  const gate = gateOf(job, jobs);
  if (gate) out.push({ label: `Gated by ${KIND_LABEL[gate.job.kind].toLowerCase()} ${shortId(gate.job.id)} · ready ${duration(gate.ageS)} before start`, jobId: gate.job.id });
  const gated = jobs.find((other) => other.kind === "campaign" && gateOf(other, jobs)?.job.id === job.id);
  if (gated) out.push({ label: `Gated campaign ${shortId(gated.id)}`, jobId: gated.id });
  if (job.publish) out.push({ label: `Publishes campaign ${shortId(job.publish.campaignJobId)}`, jobId: job.publish.campaignJobId });
  const publication = jobs.find((other) => other.publish?.campaignJobId === job.id);
  if (publication) out.push({ label: `Published by ${shortId(publication.id)}`, jobId: publication.id });
  return out;
}

// -------------------------------------------------------------- timeline

export interface TimelineEntry {
  atMs: number;
  text: string;
  detail?: string;
  tone: Tone;
  outcome?: "pass" | "fail" | "unknown";
  now?: boolean;
}

const at = (job: Job, fraction: number) => job.startMs + ((job.endMs ?? job.startMs) - job.startMs) * fraction;

// Lifecycle as the worker records it. Intermediate times for finished demo
// jobs are interpolated; the live campaign's entries come from the replay.
export function timelineOf(job: Job): TimelineEntry[] {
  const created = Date.parse(job.createdAt);
  const out: TimelineEntry[] = [{ atMs: created, text: "Created", detail: "Queued for the worker; the operator runs one job at a time.", tone: "muted" }];
  const started = job.startedAt ? Date.parse(job.startedAt) : undefined;
  const end = job.endMs ?? job.startMs;

  if (job.kind === "readiness" || job.kind === "prepare") {
    if (started) out.push({ atMs: started, text: "Worker started", detail: "Checking the selected lab environment.", tone: "neutral" });
    const checks = job.readiness?.checks ?? [];
    const s = summarize(checks);
    if (job.kind === "prepare") {
      out.push({ atMs: at(job, 0.3), text: "Repair-safe: started minh-lane", tone: "neutral" });
      out.push({ atMs: at(job, 0.62), text: "Restarted the lane RAG API", tone: "neutral" });
    }
    out.push({
      atMs: end,
      text: s.status === "READY" ? `${job.kind === "prepare" ? "Rechecked · ready" : "Ready"}` : "Blocked",
      detail: `${s.pass} passed${s.warn ? ` · ${s.warn} warning${s.warn > 1 ? "s" : ""}` : ""}${s.block ? ` · ${s.block} blocking` : ""} · ${(s.ms / 1000).toFixed(1)}s of checks`,
      tone: s.status === "READY" ? "neutral" : "warn",
    });
    return out;
  }

  if (job.kind === "publish" && job.publish) {
    if (started) out.push({ atMs: started, text: "Started from the reviewed preview", detail: `Pack ${job.publish.pack}`, tone: "neutral" });
    out.push({ atMs: at(job, 0.45), text: `Copied ${job.publish.files} files`, detail: `${PUBLISH_PREVIEW.destination}/`, tone: "neutral" });
    out.push({ atMs: at(job, 0.8), text: "Updated the data catalogs", detail: PUBLISH_PREVIEW.catalogEdits.join(", "), tone: "neutral" });
    out.push({ atMs: at(job, 0.9), text: `Committed on ${job.publish.branch}`, detail: "Only the pack and catalog paths are staged.", tone: "neutral" });
    out.push({ atMs: end, text: `Pushed to ${PUBLISH_PREVIEW.target.upstream}`, detail: "Publishing pushes the export commit to the branch's configured upstream.", tone: "neutral" });
    return out;
  }

  // Campaigns.
  if (started) out.push({ atMs: started, text: "Worker started", detail: "Preparing serial campaign.", tone: "neutral" });
  const campaign = job.campaignData;
  const view = job.view;
  if (job.live && campaign && view) {
    const finished = campaign.attempts.filter((a) => view.states[a.index] !== "pending" && view.states[a.index] !== "running");
    const shown = finished.slice(-4);
    if (finished.length > shown.length) out.push({ atMs: job.startMs + finished[0].start * 1000, text: `${finished.length - shown.length} earlier attempts`, tone: "muted" });
    for (const attempt of shown) {
      const state = view.states[attempt.index];
      out.push({
        atMs: job.startMs + attempt.end * 1000,
        text: `Attempt ${attempt.index + 1} · ${displayModel(attempt.model)} · ${humanize(attempt.caseId)}`,
        detail: state === "error" ? "Runner error; scoped teardown ran" : undefined,
        tone: state === "error" ? "warn" : "neutral",
        outcome: state === "pass" || state === "fail" || state === "unknown" ? state : undefined,
      });
    }
    if (view.current) {
      out.push({
        atMs: job.startMs + view.current.start * 1000,
        text: `Attempt ${view.current.index + 1} started · ${displayModel(view.current.model)}`,
        detail: `${humanize(view.current.caseId)}${view.currentPhase ? ` · ${view.currentPhase.label} phase` : ""}`,
        tone: "accent",
        now: true,
      });
    }
    if (job.status === "completed") out.push({ atMs: end, text: `All ${view.planned} attempts recorded`, detail: "Campaign report written; runs are in the operator's run root.", tone: "neutral" });
    if (job.status === "failed") out.push({ atMs: end, text: "Campaign stopped on a runner error", detail: "Setup could not pull the fixture image. Not counted against the model.", tone: "warn" });
    return out;
  }

  out.push({ atMs: job.startMs + 9_000, text: "Attempt 1 started", tone: "neutral" });
  if (job.status === "stopped") {
    out.push({ atMs: end - 150_000, text: "Stop requested by the operator", detail: "The worker finishes the current step, then runs teardown.", tone: "neutral" });
    out.push({ atMs: end - 18_000, text: "Teardown completed", detail: job.currentLabel, tone: "neutral" });
    out.push({ atMs: end, text: `Stopped after ${job.currentIndex} of ${job.total} attempts`, detail: "Completed results are preserved.", tone: "neutral" });
  } else if (job.status === "interrupted") {
    out.push({ atMs: end - 40_000, text: `Worker exited during attempt ${job.currentIndex + 1}`, detail: job.currentLabel, tone: "warn" });
    out.push({ atMs: end, text: "Marked interrupted", detail: "The app reconciled jobs whose worker vanished. Recorded attempts are preserved; lost attempts are never rescheduled.", tone: "warn" });
  } else if (job.status === "completed") {
    out.push({ atMs: end, text: `All ${job.total} attempts finished`, detail: job.summary, tone: "neutral" });
  }
  return out;
}

// ------------------------------------------------------------------ runs

/** Recorded runs by run_id, preferring the canonical export. */
export function useRunIndex(): Map<string, Run> {
  const query = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  return useMemo(() => {
    const map = new Map<string, Run>();
    for (const run of query.data ?? []) {
      const prev = map.get(run.run_id);
      if (!prev || run.source === "canonical") map.set(run.run_id, run);
    }
    return map;
  }, [query.data]);
}

// -------------------------------------------------------------- sessions

export interface Session {
  id: string;
  jobs: Job[];
  startMs: number;
  endMs: number;
  live: boolean;
}

const SESSION_GAP_MS = 6 * 3600_000;

/** Clusters of jobs separated by at least six idle hours, oldest first. */
export function sessionsOf(jobs: Job[]): Session[] {
  const sessions: Session[] = [];
  for (const job of byStart(jobs)) {
    const end = job.endMs ?? job.startMs;
    const last = sessions[sessions.length - 1];
    if (last && job.startMs - last.endMs < SESSION_GAP_MS) {
      last.jobs.push(job);
      last.endMs = Math.max(last.endMs, end);
      last.live ||= Boolean(job.live && job.status === "running");
    } else {
      sessions.push({ id: job.id, jobs: [job], startMs: job.startMs, endMs: end, live: Boolean(job.live && job.status === "running") });
    }
  }
  return sessions;
}

export function dayRange(startMs: number, endMs: number): string {
  const a = dayOf(startMs);
  const b = dayOf(endMs);
  if (a === b) return a;
  const [monthA] = a.split(" ");
  const [monthB, dayB] = b.split(" ");
  return monthA === monthB ? `${a}–${dayB}` : `${a} – ${b}`;
}
