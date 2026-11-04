// Shapes mirror operator_ui/results.py (public_run and case rows) so the fixture
// snapshot and the live backend are interchangeable.

export type Technique = "allStepsAtOnce" | "stepByStep" | "singleAgent" | "knowledgeAgentOnly";
export type RunSource = "canonical" | "exploratory" | "local";
export type CaseStatus = "PASS" | "FAIL" | "ERROR" | "TIMEOUT" | "UNKNOWN";

export interface RoleMetrics {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  cost?: number;
  duration_s?: number;
}

export interface CaseRow {
  case: string;
  status: CaseStatus;
  ground_truth_passed: boolean | null;
  ground_truth_configured: boolean | null;
  verified: boolean | null;
  technique: Technique | null;
  duration_s: number | null;
  metrics: Partial<Record<"api" | "debug" | "verification", RoleMetrics>>;
}

export interface Run {
  ref: string;
  run_id: string;
  source: RunSource;
  source_group: string;
  archived: boolean;
  technique: Technique | null;
  models: { API: string[]; DebugAgent: string[]; Verification: string[] };
  cases: string[];
  planned_cases: number;
  observed_cases: number;
  ground_truth_known: number;
  ground_truth_passed: number;
  ground_truth_rate: number | null;
  ground_truth_unavailable: number;
  ground_truth_missing: number;
  ground_truth_not_configured: number;
  verification_known: number;
  verification_correct: number;
  verification_comparable: number;
  total_cost: number | null;
  total_tokens: number | null;
  duration_s: number | null;
  pass_rate: number | null;
  status: "recorded" | "incomplete";
}

export interface RunWithCases extends Run {
  case_rows: CaseRow[];
}

export interface RunsSnapshot {
  generated_at: string;
  producer: string;
  runs: RunWithCases[];
}

export interface DataSourceInfo {
  mode: "fixture" | "api";
  label: string;
  generatedAt?: string;
}

export interface OverviewSnapshot {
  headline?: Record<string, unknown>;
  sources?: Record<string, number>;
  readiness?: { status: string | null; checked_at: string | null; job_id?: string | null; fresh?: boolean; ready?: boolean; reason?: string | null };
  latest_runs?: Run[];
  jobs?: OperatorJob[];
}

export interface CampaignHealthHistory {
  campaign_id: string;
  samples: { sampled_at: string; telemetry: TelemetrySample; topology: TopologySnapshot }[];
  truncated: boolean;
  reason: string | null;
}

export type JobKind = "readiness" | "prepare" | "campaign" | "publish";
export type JobStatus = "queued" | "running" | "stop_requested" | "completed" | "blocked" | "failed" | "stopped" | "interrupted";

export interface JobAttempt {
  sequence: number;
  case: string;
  technique: Technique;
  debug_model: string | null;
  repetition: number;
  status: string;
  ground_truth_passed: boolean | null;
  verified: boolean | null;
  duration_s: number | null;
  run_ref?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  return_code?: number | null;
  outcome?: string | null;
  ground_truth_configured?: boolean | null;
  report_available?: boolean;
}

export interface OperatorJob {
  id: string;
  kind: JobKind;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  current_index: number;
  total: number;
  current_label: string | null;
  attempts: JobAttempt[];
  campaign?: {
    cases: string[];
    techniques: Technique[];
    debug_models: (string | null)[];
    repetitions: number;
    api_model: string | null;
    verification_model: string | null;
  };
  result?: {
    readiness?: ReadinessResult;
    preparation?: RepairResult[];
    reason?: string;
    branch?: string;
    remote?: string;
    commit?: string;
  } | null;
  stop_requested: boolean;
}

export type EventPhase = "setup" | "knowledge" | "debug" | "verify" | "truth" | "teardown";
export type EventSource = "runner" | "kubectl" | "knowledge" | "debug" | "verifier" | "truth";
export type EventLevel = "info" | "command" | "output" | "warn" | "error" | "pass" | "fail";

export interface JobEvent {
  id: number;
  t: number;
  attempt: number;
  phase: EventPhase;
  source: EventSource;
  level: EventLevel;
  text: string;
}

export interface ReadinessCheckResult {
  name: string;
  label: string;
  status: "pass" | "fail" | "skip";
  blocking: boolean;
  hint?: string | null;
  detail?: string | null;
  duration_ms?: number | null;
  start_offset_ms?: number | null;
  commands?: {
    command?: string;
    parent_command?: string;
    stdout?: string;
    stderr?: string;
    exit_code?: number | null;
    note?: string;
  }[];
}

export interface RepairResult {
  name: string;
  label: string;
  status: "pass" | "fail" | "skip";
  message?: string | null;
  duration_ms?: number | null;
  commands?: ReadinessCheckResult["commands"];
}

export interface ReadinessResult {
  status: "READY" | "BLOCKED";
  generated_at?: string | null;
  mode?: "check-only" | "repair-safe" | null;
  checks: ReadinessCheckResult[];
  repairs?: RepairResult[];
}

export interface OperatorCase {
  id: string;
  label: string;
}

export interface TelemetrySample {
  sampled_at: string;
  stale: boolean;
  status?: "ok" | "partial" | "stale" | "unavailable";
  reason?: string | null;
  gpu_inventory_available?: boolean;
  process_inventory_available?: boolean;
  cpu: { total_pct: number | null; per_core: (number | null)[] };
  memory: { total_bytes: number | null; used_bytes: number | null; available_bytes?: number | null; cache_bytes?: number | null; percent: number | null } | null;
  disk: { path: string; total_bytes: number | null; used_bytes: number | null; free_bytes: number | null; free_gib: number | null; percent: number | null } | null;
  gpus: { index: number; name: string; utilization_pct: number | null; memory_total_bytes: number | null; memory_used_bytes: number | null; temperature_c: number | null; power_w: number | null; status?: string }[];
  processes: { pid: number; user: string | null; name: string; cpu_pct: number | null; memory_bytes: number | null; attribution: "unconfirmed" | "lane" | "shared" | "other" }[];
}

export interface TopologyNode {
  name: string;
  status: string;
  ip?: string | null;
}

export interface TopologyPod {
  name: string;
  namespace: string;
  status: string;
  ready?: string | null;
  restarts?: number | null;
  age?: string | null;
  kind?: "system" | "fixture" | "leftover" | "workload" | "unknown";
  note?: string | null;
}

export interface TopologyProfile {
  name: string;
  status: string;
  selected: boolean;
}

export interface TopologySnapshot {
  sampled_at: string;
  stale: boolean;
  status?: "ok" | "partial" | "stale" | "unavailable";
  reason?: string | null;
  profiles: TopologyProfile[];
  selected_profile: {
    name: string;
    status: string;
    kubernetes?: string | null;
    driver?: string | null;
    nodes: TopologyNode[];
    pods: TopologyPod[] | null;
  } | null;
  services: { name: string; detail?: string | null; status: string; uptime?: string | null }[];
}

export interface PublishPreview {
  campaign_job_id: string;
  preview_token: string;
  expires_at?: string;
  branch?: string;
  target?: string | { display?: string; kind?: string; worktree?: string; worktree_path?: string; remote?: string; branch?: string; base_branch?: string; base_sha?: string };
  campaign_status?: string;
  attempts_recorded?: number;
  attempts_planned?: number;
  attempts_excluded?: number;
  attempts_unstarted?: number;
  ground_truth_known?: number;
  ground_truth_passed?: number;
  verifier_known?: number;
  verifier_comparable?: number;
  verifier_agrees?: number;
  files: { path: string; status?: string; sha256?: string; lines?: number; bytes?: number }[];
  summary?: Record<string, unknown>;
  [key: string]: unknown;
}
