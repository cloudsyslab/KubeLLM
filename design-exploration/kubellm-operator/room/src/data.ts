import type { EvalCase, EventRow, LabProfile, ModelScore, ResourcePoint } from "./domain";

/** Every numeric result below is illustrative preview data, never a recorded KubeLLM evaluation. */
export const models: ModelScore[] = [
  { id: "cedar-32", label: "Cedar 32B", family: "Open model · 32B", success: 82.5, cost: 0.64, speed: 38.4, coverage: 100, attempts: 40, runs: 8, shift: 3.2, color: "#116f5b" },
  { id: "northstar", label: "Northstar Large", family: "Hosted · flagship", success: 77.5, cost: 2.14, speed: 29.8, coverage: 100, attempts: 40, runs: 8, shift: -1.4, color: "#5876d2" },
  { id: "ember-fast", label: "Ember Fast", family: "Hosted · fast", success: 71.4, cost: 0.28, speed: 75.2, coverage: 87.5, attempts: 35, runs: 7, shift: 5.6, color: "#c77d32" },
  { id: "cedar-70", label: "Cedar 70B", family: "Open model · 70B", success: 67.5, cost: 1.06, speed: 22.3, coverage: 100, attempts: 40, runs: 8, shift: 0.8, color: "#9b65a0" },
  { id: "keystone", label: "Keystone Reasoner", family: "Hosted · reasoning", success: 63.3, cost: 3.82, speed: 11.6, coverage: 75, attempts: 30, runs: 6, shift: -4.3, color: "#a9514b" },
];

export const cases: EvalCase[] = [
  { id: "wrong_port", label: "Service target mismatch", area: "Networking", scores: [100, 80, 80, 80, 60] },
  { id: "probe_delay", label: "Probe timeout", area: "Health checks", scores: [80, 80, 100, 60, 80] },
  { id: "stale_mount", label: "Stale secret mount", area: "Configuration", scores: [80, 80, 60, 80, null] },
  { id: "dns_lookup", label: "Service discovery", area: "Networking", scores: [80, 60, 80, 60, null] },
  { id: "oom_limit", label: "Memory limit", area: "Resources", scores: [80, 80, 60, 60, 60] },
  { id: "bad_selector", label: "Pod selector", area: "Scheduling", scores: [80, 80, 60, 60, 40] },
  { id: "rollout_stall", label: "Stalled rollout", area: "Deployments", scores: [80, 80, 60, 80, 60] },
  { id: "volume_claim", label: "Volume claim", area: "Storage", scores: [80, 80, 60, 60, null] },
];

export const evalHistory = [
  { id: "eval-042", label: "Week 44 · shared suite", date: "Nov 01, 2026", cases: 8, attempts: 40, technique: "stepByStep", revision: "demo:8c12fe2", duration: "22m 14s" },
  { id: "eval-039", label: "Week 43 · shared suite", date: "Oct 25, 2026", cases: 8, attempts: 40, technique: "singleAgent", revision: "demo:297db51", duration: "19m 48s" },
  { id: "eval-036", label: "Week 42 · shared suite", date: "Oct 18, 2026", cases: 8, attempts: 40, technique: "allStepsAtOnce", revision: "demo:b2ae410", duration: "24m 03s" },
];

export const events: EventRow[] = [
  { time: "00:00.000", level: "INFO", stage: "Preflight", message: "Loading the explicitly selected lane", detail: "readiness started · check-only", },
  { time: "00:00.268", level: "OK", stage: "Preflight", message: "Repository identity verified", detail: "canonical runner and case catalog available", },
  { time: "00:00.841", level: "OK", stage: "Preflight", message: "PostgreSQL connectivity passed", detail: "selected lane · pgvector service reachable", },
  { time: "00:01.125", level: "OK", stage: "Preflight", message: "Kubernetes account is available", detail: "explicit kubeconfig · selected context ready", },
  { time: "00:01.782", level: "OK", stage: "Preflight", message: "RAG service health passed", detail: "configured endpoint responded successfully", },
  { time: "00:02.010", level: "INFO", stage: "Campaign", message: "Starting attempt 17 of 40", detail: "wrong_port · stepByStep · Cedar 32B", },
  { time: "00:02.936", level: "INFO", stage: "Diagnose", message: "Diagnosis request completed", detail: "model response recorded in the private run directory", },
  { time: "00:03.172", level: "WARN", stage: "Verify", message: "Expected test fixture is active", detail: "challenge resource is ready for diagnosis", },
  { time: "00:03.716", level: "ERROR", stage: "Restore", message: "Baseline check failed after cleanup", detail: "selected case still requires teardown; see the repair plan", },
  { time: "00:04.021", level: "INFO", stage: "Campaign", message: "Attempt 17 retained for review", detail: "ground-truth outcome remains separate from teardown status", },
];

export const profiles: LabProfile[] = [
  { id: "research-lane", label: "Research lane", status: "running", context: "explicit · isolated", nodes: 1, workloads: 8, pods: 15, affected: true },
  { id: "sandbox-lane", label: "Sandbox lane", status: "running", context: "local · read only", nodes: 1, workloads: 5, pods: 9, affected: false },
  { id: "legacy-profile", label: "Legacy profile", status: "stopped", context: "local · inventory only", nodes: 0, workloads: 0, pods: 0, affected: false },
  { id: "unavailable-profile", label: "Unresolved profile", status: "unknown", context: "status could not be verified", nodes: 0, workloads: 0, pods: 0, affected: false },
];

const cpuTrace = [23, 22, 24, 28, 34, 31, 39, 36, 43, 40, 48, 42, 54, 50, 58, 51, 62, 56, 64, 58, 68, 62, 73, 67];
const gpuZero = [0, 0, 0, 8, 12, 18, 27, 42, 50, 58, 65, 61, 74, 79, 68, 84, 80, 75, 87, 82, 78, 88, 83, 81];
const gpuOne = [0, 0, 0, 0, 0, 4, 6, 12, 25, 34, 42, 50, 55, 61, 70, 64, 77, 81, 76, 84, 82, 86, 79, 83];

export const resources: ResourcePoint[] = cpuTrace.map((cpu, index) => ({
  time: `-${(23 - index) * 5}m`,
  cpu,
  memory: 44 + ((index * 7) % 13),
  gpu0: gpuZero[index],
  gpu1: gpuOne[index],
  vram0: 3.2 + gpuZero[index] * 0.095,
  vram1: 2.9 + gpuOne[index] * 0.092,
}));

export const formatRate = (value: number) => `${value.toFixed(1)}%`;
export const formatDollars = (value: number) => `$${value.toFixed(2)}`;
export const metricLabel = (metric: "success" | "cost" | "speed") =>
  metric === "success" ? "Ground Truth success" : metric === "cost" ? "Cost per attempt" : "Seconds per attempt";

export const illustrativeNotice = "Illustrative sample data · no benchmark is running";
