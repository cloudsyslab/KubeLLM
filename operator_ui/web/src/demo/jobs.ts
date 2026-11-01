import { BLOCKED_CHECKS, EARLIER_READY_CHECKS, READY_CHECKS, type ReadinessCheck } from "./readiness";

// Demo operator job history for the Jobs, Environment, New campaign, Publish,
// and active-work options. Kinds and statuses mirror operator_ui/jobs.py and
// worker.py. Campaigns that list runIds point at real recorded runs in the
// snapshot (resolve refs at runtime); everything else is illustrative.

export type JobKind = "readiness" | "prepare" | "campaign" | "publish";
export type JobStatus = "queued" | "running" | "completed" | "failed" | "stopped" | "interrupted" | "blocked";

export interface DemoJob {
  id: string;
  kind: JobKind;
  status: JobStatus;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
  total: number;
  currentIndex: number;
  currentLabel?: string;
  title: string;
  summary: string;
  /** Linked to the live demo replay (status and progress come from it). */
  live?: boolean;
  campaign?: { models: string[]; cases: number; techniques: string[]; repetitions: number; runIds?: string[] };
  readiness?: { mode: "check-only" | "repair-safe"; checks: ReadinessCheck[] };
  publish?: { campaignJobId: string; pack: string; files: number; branch: string };
}

/** "Now" for the demo history, so relative times stay stable. */
export const DEMO_NOW = "2026-11-01T20:05:00Z";

const GPT6_RUNS = ["2026-09-22T18-27-02", "2026-09-22T19-47-08", "2026-09-22T21-07-05", "2026-09-22T23-29-45", "2026-09-23T00-57-28"];
const QWEN_RUNS = ["2026-08-26T20-29-37", "2026-08-27T01-26-50", "2026-08-27T04-11-04", "2026-08-27T10-31-12", "2026-08-27T15-00-27"];

export const JOBS: DemoJob[] = [
  {
    id: "c7e2a91f40b6",
    kind: "campaign",
    status: "running",
    live: true,
    createdAt: "2026-11-01T19:12:04Z",
    startedAt: "2026-11-01T19:12:09Z",
    total: 18,
    currentIndex: 0,
    title: "2 models × 9 cases",
    summary: "gpt-6-luna and glm-4.7-flash · all steps at once · 1 repetition",
    campaign: { models: ["gpt-6-luna", "glm-4.7-flash:latest"], cases: 9, techniques: ["allStepsAtOnce"], repetitions: 1 },
  },
  {
    id: "4b19d0e7c3a2",
    kind: "readiness",
    status: "completed",
    createdAt: "2026-11-01T19:08:41Z",
    startedAt: "2026-11-01T19:08:42Z",
    finishedAt: "2026-11-01T19:09:13Z",
    total: READY_CHECKS.length,
    currentIndex: READY_CHECKS.length,
    title: "Preflight",
    summary: "Ready · 20 passed · 1 warning (Docker data root)",
    readiness: { mode: "check-only", checks: READY_CHECKS },
  },
  {
    id: "91f3c6a8e2d4",
    kind: "publish",
    status: "completed",
    createdAt: "2026-09-23T02:14:30Z",
    startedAt: "2026-09-23T02:14:31Z",
    finishedAt: "2026-09-23T02:15:58Z",
    total: 0,
    currentIndex: 0,
    title: "Publish operator-campaign-2026-09-22-e08b7d2c",
    summary: "Sanitized exploratory pack committed under data/exploratory/ and pushed to origin/minh",
    publish: { campaignJobId: "e08b7d2c51f9", pack: "operator-campaign-2026-09-22-e08b7d2c", files: 946, branch: "minh" },
  },
  {
    id: "e08b7d2c51f9",
    kind: "campaign",
    status: "completed",
    createdAt: "2026-09-22T18:26:51Z",
    startedAt: "2026-09-22T18:27:00Z",
    finishedAt: "2026-09-23T02:12:10Z",
    total: 135,
    currentIndex: 135,
    title: "gpt-6-luna × 27 cases × 5",
    summary: "135 attempts recorded · 124 passed Ground Truth",
    campaign: { models: ["gpt-6-luna"], cases: 27, techniques: ["allStepsAtOnce"], repetitions: 5, runIds: GPT6_RUNS },
  },
  {
    id: "5d2e8a0c7f13",
    kind: "readiness",
    status: "completed",
    createdAt: "2026-09-22T18:20:02Z",
    startedAt: "2026-09-22T18:20:03Z",
    finishedAt: "2026-09-22T18:20:36Z",
    total: EARLIER_READY_CHECKS.length,
    currentIndex: EARLIER_READY_CHECKS.length,
    title: "Preflight",
    summary: "Ready",
    readiness: { mode: "check-only", checks: EARLIER_READY_CHECKS },
  },
  {
    id: "a3c90f6b2e17",
    kind: "prepare",
    status: "completed",
    createdAt: "2026-09-22T18:12:44Z",
    startedAt: "2026-09-22T18:12:45Z",
    finishedAt: "2026-09-22T18:16:31Z",
    total: EARLIER_READY_CHECKS.length,
    currentIndex: EARLIER_READY_CHECKS.length,
    title: "Prepare environment",
    summary: "Started minh-lane, restarted the lane RAG API, rechecked: ready",
    readiness: { mode: "repair-safe", checks: EARLIER_READY_CHECKS },
  },
  {
    id: "f61b4e9d08a5",
    kind: "readiness",
    status: "blocked",
    createdAt: "2026-09-22T18:09:10Z",
    startedAt: "2026-09-22T18:09:11Z",
    finishedAt: "2026-09-22T18:09:40Z",
    total: BLOCKED_CHECKS.length,
    currentIndex: BLOCKED_CHECKS.length,
    title: "Preflight",
    summary: "Blocked · minikube_status, cluster_access, and the lane RAG API failed",
    readiness: { mode: "check-only", checks: BLOCKED_CHECKS },
  },
  {
    id: "2c7a5e1f9b08",
    kind: "campaign",
    status: "stopped",
    createdAt: "2026-09-19T14:02:17Z",
    startedAt: "2026-09-19T14:02:25Z",
    finishedAt: "2026-09-19T14:41:52Z",
    total: 27,
    currentIndex: 9,
    currentLabel: "port_mismatch · allStepsAtOnce · gpt-5.6-luna · repetition 1",
    title: "gpt-5.6-luna × 27 cases",
    summary: "Stopped by the operator after 9 of 27 attempts; teardown completed",
    campaign: { models: ["gpt-5.6-luna"], cases: 27, techniques: ["allStepsAtOnce"], repetitions: 1 },
  },
  {
    id: "8e4f2b6a1c3d",
    kind: "campaign",
    status: "interrupted",
    createdAt: "2026-09-02T09:15:40Z",
    startedAt: "2026-09-02T09:15:48Z",
    finishedAt: "2026-09-02T10:03:12Z",
    total: 27,
    currentIndex: 14,
    currentLabel: "readiness_failure_slow_start · knowledgeAgentOnly · gpt-5-nano · repetition 1",
    title: "gpt-5-nano × 27 cases · knowledge agent only",
    summary: "Worker exited unexpectedly at attempt 15; the operator app marked the job interrupted",
    campaign: { models: ["gpt-5-nano"], cases: 27, techniques: ["knowledgeAgentOnly"], repetitions: 1 },
  },
  {
    id: "0b9d3f7e5a26",
    kind: "campaign",
    status: "completed",
    createdAt: "2026-08-26T20:29:20Z",
    startedAt: "2026-08-26T20:29:37Z",
    finishedAt: "2026-08-27T19:08:45Z",
    total: 135,
    currentIndex: 135,
    title: "qwen3.8:27b × 27 cases × 5",
    summary: "134 attempts recorded · 1 planned case missing; outcomes left unknown",
    campaign: { models: ["qwen3.8:27b"], cases: 27, techniques: ["allStepsAtOnce"], repetitions: 5, runIds: QWEN_RUNS },
  },
];

export const jobById = (id: string) => JOBS.find((job) => job.id === id);

export const KIND_LABEL: Record<JobKind, string> = {
  readiness: "Preflight",
  prepare: "Preparation",
  campaign: "Campaign",
  publish: "Publication",
};

/**
 * What a publication preview lists for the latest completed campaign that has
 * not been published (the qwen3.8:27b campaign; its counts match the recorded
 * runs in the snapshot). Mirrors operator_ui/publishing.py: a private preview
 * is reviewed first; publishing copies the reviewed files into
 * data/exploratory/<pack>/, updates the two data catalogs, commits only those
 * paths on the current branch, and then pushes that commit to the branch's
 * configured upstream.
 */
export const PUBLISH_PREVIEW = {
  campaignJobId: "0b9d3f7e5a26",
  pack: "operator-campaign-2026-08-26-0b9d3f7e",
  destination: "data/exploratory/operator-campaign-2026-08-26-0b9d3f7e",
  layout: "<technique>/attempt-<NNNN>-<case>/",
  target: { branch: "minh", head: "4522220", upstream: "origin/minh" },
  /** One planned case result is missing from the recorded runs; it is counted as lacking exportable structure. */
  attempts: { recorded: 134, planned: 135, unstarted: 0, excluded: 1 },
  groundTruth: { known: 115, passed: 94 },
  verifier: { known: 115, comparable: 115, agrees: 112 },
  models: { API: "gpt-5-mini", DebugAgent: "qwen3.8:27b", Verification: "gpt-5-nano" },
  techniques: ["allStepsAtOnce"],
  /** Written once per attempt directory. */
  perAttemptFiles: ["run_config.archived.json", "provenance.archived.json", "aggregate.json"],
  /** Written per case inside each attempt directory. */
  perCaseFiles: ["summary.json", "ground_truth.json", "verification_report.meta.json", "config_effective.json"],
  packFiles: ["README.md"],
  catalogEdits: ["data/README.md", "data/exploratory/README.md"],
  totalFiles: 939,
  excluded: "Raw logs, progress traces, prompts, generated commands, free-form results, endpoints, credentials, and private lane details",
  marker: "run_config.archived.json keeps the pack out of canonical analysis",
};
