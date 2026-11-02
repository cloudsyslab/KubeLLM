import type { CaseRow, RunWithCases } from "@/api/types";
import cases from "@/data/cases.json";
import { caseOutcome } from "@/lib/explore";

// A scripted demo campaign for the options room. Outcomes, verifier
// judgments, and per-role timings replay the latest recorded canonical run of
// each model; only the command output, telemetry, and topology are simulated.

export const DEMO_MODELS = ["gpt-6-luna", "glm-4.7-flash:latest"] as const;
export const DEMO_CASES = [
  "environment_variable",
  "incorrect_selector",
  "liveness_probe_wrong_path",
  "missing_dependency",
  "port_mismatch_named_target",
  "readiness_failure_slow_start",
  "resource_limits_oom",
  "wrong_interface_bind_address",
  "wrong_port_9090",
];
/** Attempt that fails during setup when the failure branch is on. */
export const FAILURE_ATTEMPT = 12;

/** Demo cases whose fixture ships a Service (app_service.yaml), by its real name. */
export const SERVICE_NAMES: Record<string, string> = {
  incorrect_selector: "app-service",
  port_mismatch_named_target: "named-target-service",
  wrong_interface_bind_address: "wrong-interface-bind-address-service",
};

export type PhaseKey = "setup" | "knowledge" | "debug" | "verify" | "truth" | "teardown";
export const PHASES: { key: PhaseKey; label: string }[] = [
  { key: "setup", label: "Setup" },
  { key: "knowledge", label: "Knowledge" },
  { key: "debug", label: "Debug" },
  { key: "verify", label: "Verify" },
  { key: "truth", label: "Ground Truth" },
  { key: "teardown", label: "Teardown" },
];

export type Source = "runner" | "kubectl" | "knowledge" | "debug" | "verifier" | "truth";
export type Level = "info" | "command" | "output" | "warn" | "error" | "pass" | "fail";

export interface DemoEvent {
  t: number;
  attempt: number;
  phase: PhaseKey;
  source: Source;
  level: Level;
  text: string;
}

export interface DemoPhase {
  key: PhaseKey;
  label: string;
  start: number;
  end: number;
  tokens?: number;
}

export interface DemoAttempt {
  index: number;
  model: string;
  caseId: string;
  outcome: "pass" | "fail" | "unknown";
  verified: boolean | null;
  start: number;
  end: number;
  phases: DemoPhase[];
  sourceRunId: string;
}

export interface DemoCampaign {
  id: string;
  title: string;
  attempts: DemoAttempt[];
  events: DemoEvent[];
  total: number;
  failure: boolean;
  sourceRuns: { model: string; runId: string }[];
}

interface CaseInfo {
  symptom: string;
  checks: string[];
}
const CASE_INFO = (cases as unknown as { cases: Record<string, CaseInfo> }).cases;

// Deterministic noise so the replay is identical on every load and scrub.
export function noise(seed: number): number {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

const appName = (caseId: string) => caseId.replaceAll("_", "-").slice(0, 28);
const podIp = (index: number) => `10.244.0.${20 + index}`;

function latestRun(runs: RunWithCases[], model: string): RunWithCases | undefined {
  return runs
    .filter((run) => run.source === "canonical" && run.models.DebugAgent.includes(model))
    .sort((a, b) => b.run_id.localeCompare(a.run_id))[0];
}

function phaseSeconds(row: CaseRow | undefined): Record<PhaseKey, number> {
  const knowledge = row?.metrics.api?.duration_s ?? 30;
  const debug = row?.metrics.debug?.duration_s ?? 60;
  const verify = row?.metrics.verification?.duration_s ?? 30;
  const total = Math.max(row?.duration_s ?? knowledge + debug + verify + 30, knowledge + debug + verify + 12);
  const rest = total - knowledge - debug - verify;
  return { setup: rest * 0.45, knowledge, debug, verify, truth: rest * 0.15, teardown: rest * 0.4 };
}

function phaseEvents(attempt: DemoAttempt, phase: DemoPhase, apiModel: string, failing: boolean): Omit<DemoEvent, "t" | "attempt" | "phase">[] {
  const app = appName(attempt.caseId);
  const info = CASE_INFO[attempt.caseId];
  const passed = attempt.outcome === "pass";
  switch (phase.key) {
    case "setup":
      if (failing) {
        return [
          { source: "runner", level: "info", text: `attempt ${attempt.index + 1} · ${attempt.model} · ${attempt.caseId}` },
          { source: "kubectl", level: "command", text: `kubectl --context minh-lane apply -f ${attempt.caseId}.yaml` },
          { source: "kubectl", level: "output", text: `pod/${app} created` },
          { source: "kubectl", level: "command", text: `kubectl --context minh-lane wait --for=condition=PodScheduled pod/${app} --timeout=120s` },
          { source: "kubectl", level: "warn", text: `Back-off pulling image "kubellm/${app}:latest"` },
          { source: "runner", level: "error", text: `setup failed: ErrImagePull for kubellm/${app}:latest; fixture image is missing from the lane's Docker daemon` },
          { source: "runner", level: "info", text: "running scoped teardown before stopping the campaign" },
        ];
      }
      return [
        { source: "runner", level: "info", text: `attempt ${attempt.index + 1} · ${attempt.model} · ${attempt.caseId}` },
        { source: "kubectl", level: "command", text: `kubectl --context minh-lane apply -f ${attempt.caseId}.yaml` },
        { source: "kubectl", level: "output", text: `pod/${app} created` },
        ...(SERVICE_NAMES[attempt.caseId] ? [{ source: "kubectl" as const, level: "output" as const, text: `service/${SERVICE_NAMES[attempt.caseId]} created` }] : []),
        { source: "runner", level: "info", text: `fixture ready · symptom: "${info?.symptom ?? "recorded symptom unavailable"}"` },
      ];
    case "knowledge":
      return [
        { source: "knowledge", level: "info", text: `knowledge agent (${apiModel}) reading the symptom` },
        { source: "knowledge", level: "output", text: "retrieved 4 passages · learnk8s.io/troubleshooting-deployments" },
        { source: "knowledge", level: "info", text: "plan drafted: inspect pod, events, and manifest; apply the smallest fix; re-check the symptom" },
      ];
    case "debug":
      return [
        { source: "debug", level: "command", text: "kubectl --context minh-lane get pods -o wide" },
        { source: "debug", level: "output", text: `${app}   0/1   Running   0   ${Math.round(phase.start - attempt.start)}s   ${podIp(attempt.index)}` },
        { source: "debug", level: "command", text: `kubectl --context minh-lane describe pod ${app}` },
        { source: "debug", level: "output", text: "Environment: OPENAI_API_KEY=[redacted]  APP_PORT=8765" },
        { source: "debug", level: "command", text: `kubectl --context minh-lane logs ${app} --tail=40` },
        { source: "debug", level: "command", text: `kubectl --context minh-lane apply -f /tmp/${app}-edited.yaml` },
        { source: "debug", level: "output", text: `pod/${app} configured` },
        { source: "debug", level: "info", text: `debug agent (${attempt.model}) declares the issue ${passed ? "fixed" : "fixed; verification pending"}` },
      ];
    case "verify":
      return [
        { source: "verifier", level: "command", text: `curl -s -o /dev/null -w "%{http_code}" http://${podIp(attempt.index)}:8765` },
        { source: "verifier", level: "output", text: passed ? "200" : "000 (connection timed out)" },
        {
          source: "verifier",
          level: "info",
          text: `verifier judgment: ${attempt.verified === null ? "not recorded" : attempt.verified ? "repaired" : "not repaired"}`,
        },
      ];
    case "truth": {
      const checks = info?.checks ?? ["Recorded checks unavailable"];
      // An unknown outcome is neither a pass nor a failure: no check marks, neutral level.
      if (attempt.outcome === "unknown") {
        return [
          ...checks.map((check) => ({ source: "truth" as const, level: "info" as Level, text: `· ${check}` })),
          { source: "runner", level: "info", text: "Ground Truth: UNKNOWN (no recorded outcome)" },
        ];
      }
      return [
        ...checks.map((check, i) => ({
          source: "truth" as const,
          level: (passed || i < checks.length - 1 ? "pass" : "fail") as Level,
          text: `${passed || i < checks.length - 1 ? "✓" : "✗"} ${check}`,
        })),
        { source: "runner", level: passed ? "pass" : "fail", text: `Ground Truth: ${passed ? "PASS" : "FAIL"}` },
      ];
    }
    case "teardown":
      return [
        { source: "kubectl", level: "command", text: `kubectl --context minh-lane delete -f ${attempt.caseId}.yaml --wait` },
        { source: "kubectl", level: "output", text: `pod "${app}" deleted` },
        { source: "runner", level: "info", text: "teardown verified: lane restored to its baseline" },
      ];
  }
}

export function buildCampaign(runs: RunWithCases[], failure: boolean): DemoCampaign {
  const sources = DEMO_MODELS.map((model) => ({ model, run: latestRun(runs, model) }));
  const attempts: DemoAttempt[] = [];
  const events: DemoEvent[] = [];
  let clock = 0;
  const order = sources.flatMap(({ model, run }) => DEMO_CASES.map((caseId) => ({ model, run, caseId })));

  for (const [index, { model, run, caseId }] of order.entries()) {
    const row = run?.case_rows.find((r) => r.case === caseId);
    const failing = failure && index === FAILURE_ATTEMPT;
    const seconds = phaseSeconds(row);
    const phases: DemoPhase[] = [];
    let cursor = clock;
    for (const phase of PHASES) {
      const length = failing ? (phase.key === "setup" ? 48 : phase.key === "teardown" ? 22 : 0) : seconds[phase.key];
      if (length <= 0) continue;
      const tokens = phase.key === "knowledge" ? row?.metrics.api?.total_tokens : phase.key === "debug" ? row?.metrics.debug?.total_tokens : phase.key === "verify" ? row?.metrics.verification?.total_tokens : undefined;
      phases.push({ key: phase.key, label: phase.label, start: cursor, end: cursor + length, tokens });
      cursor += length;
    }
    const attempt: DemoAttempt = {
      index,
      model,
      caseId,
      outcome: failing ? "unknown" : row ? caseOutcome(row) : "unknown",
      verified: failing ? null : (row?.verified ?? null),
      start: clock,
      end: cursor,
      phases,
      sourceRunId: run?.run_id ?? "unrecorded",
    };
    attempts.push(attempt);
    const apiModel = run?.models.API[0] ?? "gpt-5-mini";
    for (const phase of phases) {
      const lines = phaseEvents(attempt, phase, apiModel, failing);
      lines.forEach((line, i) => {
        const span = phase.end - phase.start;
        const at = phase.start + span * ((i + 0.35 + noise(index * 31 + i) * 0.4) / (lines.length + 0.4));
        events.push({ ...line, t: at, attempt: index, phase: phase.key });
      });
    }
    clock = cursor + 4;
    if (failing) break;
  }

  return {
    id: failure ? "demo-campaign-failed" : "demo-campaign",
    title: `${DEMO_MODELS.length} models × ${DEMO_CASES.length} cases`,
    attempts,
    events: events.sort((a, b) => a.t - b.t),
    total: clock,
    failure,
    sourceRuns: sources.map(({ model, run }) => ({ model, runId: run?.run_id ?? "unrecorded" })),
  };
}

export type AttemptState = "pending" | "running" | "pass" | "fail" | "unknown" | "error";

export interface CampaignView {
  t: number;
  status: "running" | "completed" | "failed";
  current?: DemoAttempt;
  currentPhase?: DemoPhase;
  states: AttemptState[];
  done: number;
  planned: number;
  events: DemoEvent[];
}

function lastIndexAtOrBefore(events: DemoEvent[], t: number): number {
  let lo = 0;
  let hi = events.length - 1;
  let found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (events[mid].t <= t) {
      found = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return found;
}

export function viewAt(campaign: DemoCampaign, t: number): CampaignView {
  const planned = DEMO_MODELS.length * DEMO_CASES.length;
  const states: AttemptState[] = Array.from({ length: planned }, () => "pending");
  let current: DemoAttempt | undefined;
  let done = 0;
  for (const attempt of campaign.attempts) {
    const failing = campaign.failure && attempt.index === FAILURE_ATTEMPT;
    if (t >= attempt.end) {
      states[attempt.index] = failing ? "error" : attempt.outcome;
      done += 1;
    } else if (t >= attempt.start) {
      states[attempt.index] = "running";
      current = attempt;
    }
  }
  const currentPhase = current?.phases.find((phase) => t >= phase.start && t < phase.end);
  const failedOut = campaign.failure && t >= campaign.total - 4;
  return {
    t,
    status: failedOut ? "failed" : t >= campaign.total ? "completed" : "running",
    current,
    currentPhase,
    states,
    done,
    planned,
    events: campaign.events.slice(0, lastIndexAtOrBefore(campaign.events, t) + 1),
  };
}
