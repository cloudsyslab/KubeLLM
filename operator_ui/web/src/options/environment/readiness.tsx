import clsx from "clsx";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Circle, CircleMinus, CircleX, LoaderCircle, TriangleAlert } from "lucide-react";
import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { api } from "@/api/client";
import type { OperatorJob, ReadinessCheckResult } from "@/api/types";
import { Segmented, Tag, Tip } from "@/components/ui";
import { DEMO_NOW, JOBS, type DemoJob } from "@/demo/jobs";
import { BLOCKED_CHECKS, GROUPS, LANE, READINESS_TTL_MIN, READY_CHECKS, summarize, type CheckLevel, type ReadinessCheck } from "@/demo/readiness";

// Shared demo readiness for the Environment and New campaign options.
//
// Mirrors operator_ui: a preflight job runs check_readiness.py --check-only; a
// preparation job runs it --repair-safe, then rechecks --check-only
// (worker._run_readiness_job). A READY result stays fresh for 20 minutes
// (app._readiness_fresh), and a campaign is refused without one. Everything
// here is simulated in the browser and must be tagged Demo where shown.

// ---------------------------------------------------------------- demo clock

const LOADED_AT = Date.now();
const DEMO_EPOCH = Date.parse(DEMO_NOW);
/** Demo "now": DEMO_NOW at page load, then real time. */
export const demoNow = () => DEMO_EPOCH + (Date.now() - LOADED_AT);
export const TTL_MS = READINESS_TTL_MIN * 60_000;

/** Re-renders every `ms` with the demo time. */
export function useDemoNow(ms = 1000): number {
  const [now, setNow] = useState(demoNow);
  useEffect(() => {
    const id = window.setInterval(() => setNow(demoNow()), ms);
    return () => window.clearInterval(id);
  }, [ms]);
  return now;
}

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true);
  useEffect(() => {
    const query = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!query) return;
    const sync = () => setReduced(query.matches);
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);
  return reduced;
}

// ---------------------------------------------------------------- formatting

export const ms = (value: number) => (value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(value < 10_000 ? 1 : 0)} s`);

export function countdown(msLeft: number): string {
  const total = Math.max(0, Math.ceil(msLeft / 1000));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function ago(msAgo: number): string {
  const s = Math.max(0, Math.round(msAgo / 1000));
  if (s < 45) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} h ${m % 60} min ago`;
  const d = Math.round(h / 24);
  return `${d} ${d === 1 ? "day" : "days"} ago`;
}

export function stamp(epoch: number): string {
  const date = new Date(epoch);
  return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })} · ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })}`;
}

// ---------------------------------------------------------------- repairs

/**
 * What preparation (check_readiness.py --repair-safe) may change, with the
 * repair names and labels from operator_ui/safe.py and the limits in the
 * script. `checks` lists the readiness checks each repair can turn around.
 */
export const REPAIRS: { name: string; label: string; does: string; limit: string; checks: string[] }[] = [
  { name: "prepare_env", label: "Lab service configuration", does: "Creates .env from .env.example with mode 0600, or restricts an existing .env to 0600.", limit: "Credential placeholders stay commented; no value is invented.", checks: ["providers_api"] },
  { name: "virtual_environment", label: "Python environment", does: "Installs the pinned workspace dependencies from requirements.lock into .venv.", limit: "A .venv that is not a regular directory is never replaced.", checks: ["venv_python", "python_imports", "pytest"] },
  { name: "minikube_profile", label: "Kubernetes cluster", does: `Starts the selected profile ${LANE.profile} and verifies its lane-owned node.`, limit: "Needs 20 GiB free on the Docker data root. Other profiles are never changed.", checks: ["minikube_status", "cluster_access"] },
  { name: "kubeconfig", label: "Kubernetes access", does: "Refreshes the lane's dedicated kubeconfig and verifies API readiness.", limit: "Existing kubeconfigs are not replaced; the default context is never switched.", checks: ["kubeconfig_owner", "cluster_access"] },
  { name: "rag_api", label: "RAG service", does: `Starts a RAG API for this checkout and lane at ${LANE.ragApi.replace("http://", "")}.`, limit: "An incompatible service on that port is never stopped or adopted.", checks: ["rag_lane", "rag_api"] },
  { name: "pgvector", label: "PostgreSQL/pgvector", does: `Starts the lane's own container ${LANE.pgvector}.`, limit: "A container with that name owned by another lane is not touched.", checks: ["pgvector_owner", "db_connectivity"] },
];

const REPAIRABLE = new Set(REPAIRS.flatMap((r) => r.checks));
export const isRepairable = (check: ReadinessCheck) => check.repairable === true || REPAIRABLE.has(check.id);
export const repairsFor = (checkId: string) => REPAIRS.filter((r) => r.checks.includes(checkId));

export interface RepairResult {
  name: string;
  label: string;
  ok: boolean;
  message: string;
  ms: number;
  commands?: ReadinessCheckResult["commands"];
}

// Repair outcomes, worded as check_readiness.py words them.
const HEALTHY_REPAIRS: RepairResult[] = [
  { name: "minikube_profile", label: "Kubernetes cluster", ok: true, message: "The selected Minikube profile is already running with its expected lane-owned node.", ms: 1450 },
  { name: "kubeconfig", label: "Kubernetes access", ok: true, message: "Refreshed a dedicated workspace kubeconfig and verified API readiness.", ms: 820 },
];
const DISK_BLOCKED_REPAIRS: RepairResult[] = [
  { name: "minikube_profile", label: "Kubernetes cluster", ok: false, message: "Docker data root has 11.2 GiB free; at least 20 GiB is required before starting the selected profile.", ms: 1210 },
  { name: "dependent_services", label: "Dependent lab services", ok: false, message: "Skipped lane service repairs because the selected Minikube profile is not ready.", ms: 60 },
];

// ---------------------------------------------------------------- store

export type Mode = "check-only" | "repair-safe";
export type Scenario = "stale" | "fresh" | "blocked";

export interface ReadinessRun {
  id: string;
  kind: "readiness" | "prepare";
  mode: Mode;
  status: "READY" | "BLOCKED";
  startedAt: number;
  finishedAt: number;
  checks: ReadinessCheck[];
  repairs: RepairResult[];
  summary: string;
  origin: "history" | "session" | "scenario";
}

export interface ActiveRun {
  id: string;
  kind: "readiness" | "prepare";
  /** Prepare runs a repair-safe pass, then a check-only recheck. */
  pass: "repair" | "recheck" | "check";
  /** current_label as worker.py sets it. */
  label: string;
  startedAt: number;
  done: ReadinessCheck[];
  current?: ReadinessCheck;
  currentRepair?: RepairResult;
  repairs: RepairResult[];
  total: number;
  /** Every check this pass will run, in order. */
  target: ReadinessCheck[];
  /** Polite, throttled announcement for screen readers. */
  announce: string;
}

interface State {
  scenario: Scenario;
  history: ReadinessRun[];
  session: ReadinessRun[];
  scenarioRun?: ReadinessRun;
  active?: ActiveRun;
}

const toEpoch = (iso?: string) => (iso ? Date.parse(iso) : 0);

function fromJob(job: DemoJob): ReadinessRun {
  return {
    id: job.id,
    kind: job.kind === "prepare" ? "prepare" : "readiness",
    mode: job.readiness?.mode ?? "check-only",
    status: job.status === "completed" ? "READY" : "BLOCKED",
    startedAt: toEpoch(job.startedAt),
    finishedAt: toEpoch(job.finishedAt),
    checks: job.readiness?.checks ?? [],
    repairs: job.kind === "prepare" ? [
      { name: "minikube_profile", label: "Kubernetes cluster", ok: true, message: "Started and verified the selected Docker-backed Minikube profile.", ms: 61_000 },
      { name: "rag_api", label: "RAG service", ok: true, message: "Started a RAG API for the selected checkout and personal lane.", ms: 9_400 },
    ] : [],
    summary: job.summary,
    origin: "history",
  };
}

const HISTORY: ReadinessRun[] = JOBS.filter((job) => job.kind === "readiness" || job.kind === "prepare").map(fromJob).sort((a, b) => b.finishedAt - a.finishedAt);

const hex = () => Array.from({ length: 12 }, () => Math.floor(Math.random() * 16).toString(16)).join("");

function scenarioRun(scenario: Scenario): ReadinessRun | undefined {
  if (scenario === "stale") return undefined;
  const now = demoNow();
  const blocked = scenario === "blocked";
  return {
    id: "demo-" + scenario,
    kind: "readiness",
    mode: "check-only",
    status: blocked ? "BLOCKED" : "READY",
    startedAt: now - (blocked ? 2.5 : 4.5) * 60_000,
    finishedAt: now - (blocked ? 2 : 4) * 60_000,
    checks: blocked ? BLOCKED_CHECKS : READY_CHECKS,
    repairs: [],
    summary: blocked ? "Blocked · minikube_status, cluster_access, and the lane RAG API failed" : "Ready · 20 passed · 1 warning (Docker data root)",
    origin: "scenario",
  };
}

let state: State = { scenario: "stale", history: HISTORY, session: [] };
const listeners = new Set<() => void>();
const emit = (next: Partial<State>) => {
  state = { ...state, ...next };
  listeners.forEach((listener) => listener());
};
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

/** Every run, newest first: this session's, the demo state's, then history. */
export function allRuns(s: State = state): ReadinessRun[] {
  return [...s.session, ...(s.scenarioRun ? [s.scenarioRun] : []), ...s.history].sort((a, b) => b.finishedAt - a.finishedAt);
}

/** The lane is healthy unless the demo state stopped its profile. */
const laneHealthy = () => {
  const latest = allRuns()[0];
  return !(state.scenario === "blocked" && latest?.status === "BLOCKED");
};

let timer: number | undefined;

function startRun(kind: "readiness" | "prepare") {
  if (state.active) return;
  const healthy = laneHealthy();
  const checks = healthy ? READY_CHECKS : BLOCKED_CHECKS;
  const repairs = healthy ? HEALTHY_REPAIRS : DISK_BLOCKED_REPAIRS;
  const id = hex();
  const startedAt = demoNow();
  const passes: ActiveRun["pass"][] = kind === "prepare" ? ["repair", "recheck"] : ["check"];
  const labels: Record<ActiveRun["pass"], string> = {
    check: "Checking the selected lab environment.",
    repair: "Checking the selected lab environment.",
    recheck: "Rechecking readiness after environment preparation.",
  };

  type Step = { pass: ActiveRun["pass"]; check?: ReadinessCheck; repair?: RepairResult };
  const steps: Step[] = [];
  for (const pass of passes) {
    for (const check of checks) {
      // check_readiness.py runs the cluster repairs before the kubeconfig
      // checks, and service repairs before the RAG check.
      if (pass === "repair" && check.id === "kubeconfig_owner") repairs.forEach((repair) => steps.push({ pass, repair }));
      steps.push({ pass, check });
    }
  }

  emit({ active: { id, kind, pass: passes[0], label: labels[passes[0]], startedAt, done: [], repairs: [], total: checks.length, target: checks, announce: `${kind === "prepare" ? "Preparation" : "Preflight"} started.` } });

  let index = 0;
  const advance = () => {
    const active = state.active;
    if (!active || active.id !== id) return;
    const step = steps[index];
    if (!step) {
      const summary = summarize(checks);
      const run: ReadinessRun = {
        id,
        kind,
        mode: kind === "prepare" ? "repair-safe" : "check-only",
        status: summary.status,
        startedAt,
        finishedAt: demoNow(),
        checks,
        repairs: kind === "prepare" ? repairs : [],
        summary:
          summary.status === "READY"
            ? `Ready · ${summary.pass} passed${summary.warn ? ` · ${summary.warn} warning (Docker data root)` : ""}`
            : `Blocked · ${checks.filter((c) => c.level === "block").map((c) => c.label).join(", ")}`,
        origin: "session",
      };
      emit({ active: undefined, session: [run, ...state.session] });
      announceFinal(run);
      return;
    }
    // Moving into a new pass resets the visible check list.
    const passChanged = step.pass !== active.pass;
    const base: ActiveRun = passChanged ? { ...active, pass: step.pass, label: labels[step.pass], done: [], announce: labels[step.pass] } : active;
    if (step.repair) {
      emit({ active: { ...base, current: undefined, currentRepair: step.repair } });
      timer = window.setTimeout(() => {
        const now = state.active;
        if (!now || now.id !== id) return;
        emit({ active: { ...now, currentRepair: undefined, repairs: [...now.repairs, step.repair!], announce: `${step.repair!.label}: ${step.repair!.ok ? "done" : "not repaired"}.` } });
        index += 1;
        advance();
      }, step.repair.ms);
      return;
    }
    const check = step.check!;
    emit({ active: { ...base, current: check, currentRepair: undefined } });
    timer = window.setTimeout(() => {
      const now = state.active;
      if (!now || now.id !== id) return;
      const done = [...now.done, check];
      const group = GROUPS.find((g) => g.id === check.group);
      const groupDone = !checks.some((c) => c.group === check.group && !done.includes(c));
      emit({ active: { ...now, done, current: undefined, announce: groupDone ? `${group?.label ?? check.group} checked: ${done.filter((c) => c.group === check.group && c.level !== "pass").length || "no"} issues.` : now.announce } });
      index += 1;
      advance();
    }, check.ms);
  };
  advance();
}

let finalMessage = "";
function announceFinal(run: ReadinessRun) {
  const s = summarize(run.checks);
  finalMessage = run.status === "READY" ? `Ready. ${s.pass} passed, ${s.warn} warning. Fresh for ${READINESS_TTL_MIN} minutes.` : `Blocked. ${s.block} blocking checks.`;
  emit({});
}

export const readiness = {
  run: () => api.isLive ? api.runReadiness() : startRun("readiness"),
  prepare: () => api.isLive ? api.prepare() : startRun("prepare"),
  setScenario(scenario: Scenario) {
    if (timer) window.clearTimeout(timer);
    emit({ scenario, scenarioRun: scenarioRun(scenario), session: [], active: undefined });
  },
};

export function useReadiness() {
  const s = useSyncExternalStore(subscribe, () => state);
  const runs = allRuns(s);
  return { ...s, runs, latest: runs[0], finalMessage };
}

export type Freshness =
  | { state: "checking"; active: ActiveRun; latest?: ReadinessRun }
  | { state: "never" }
  | { state: "blocked"; latest: ReadinessRun; age: number }
  | { state: "stale"; latest: ReadinessRun; age: number; reason?: string }
  | { state: "fresh"; latest: ReadinessRun; age: number; left: number };

export function freshnessOf(latest: ReadinessRun | undefined, active: ActiveRun | undefined, now: number): Freshness {
  if (active) return { state: "checking", active, latest };
  if (!latest) return { state: "never" };
  const age = now - latest.finishedAt;
  if (latest.status === "BLOCKED") return { state: "blocked", latest, age };
  if (age > TTL_MS) return { state: "stale", latest, age };
  return { state: "fresh", latest, age, left: TTL_MS - age };
}

/** Readiness, freshness, and the launch gate, re-evaluated every second. */
export function useFreshness() {
  const local = useReadiness();
  const demoTime = useDemoNow();
  const [realTime, setRealTime] = useState(Date.now());
  useEffect(() => {
    if (!api.isLive) return;
    const id = window.setInterval(() => setRealTime(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const jobsQuery = useQuery({ queryKey: ["operator-jobs"], queryFn: api.jobs, enabled: api.isLive, refetchInterval: 1_500, staleTime: 0, retry: 0 });
  const overviewQuery = useQuery({ queryKey: ["operator-overview"], queryFn: api.overview, enabled: api.isLive, refetchInterval: 10_000, staleTime: 0, retry: 0 });
  const now = api.isLive ? realTime : demoTime;
  if (!api.isLive) {
    const fresh = freshnessOf(local.latest, local.active, now);
    return { ...local, now, fresh, busy: Boolean(local.active), canLaunch: fresh.state === "fresh", error: undefined as Error | undefined };
  }
  const all = jobsQuery.data ?? [];
  const toRun = (job: OperatorJob): ReadinessRun => {
    const result = job.result?.readiness;
    const checks = (result?.checks ?? []).map((check) => fromOperatorCheck(check));
    return {
      id: job.id,
      kind: job.kind === "prepare" ? "prepare" : "readiness",
      mode: result?.mode ?? "check-only",
      status: result?.status ?? (job.status === "completed" ? "READY" : "BLOCKED"),
      startedAt: Date.parse(job.started_at ?? job.created_at),
      finishedAt: Date.parse(job.finished_at ?? job.updated_at),
      checks,
      repairs: (result?.repairs ?? []).map((repair) => ({ name: repair.name, label: repair.label, ok: repair.status === "pass", message: repair.message ?? "", ms: repair.duration_ms ?? 0, commands: repair.commands })),
      summary: job.current_label ?? job.status,
      origin: "history",
    };
  };
  const readinessJobs = all.filter((job) => job.kind === "readiness" || job.kind === "prepare").sort((a, b) => Date.parse(b.finished_at ?? b.created_at) - Date.parse(a.finished_at ?? a.created_at));
  const activeJob = readinessJobs.find((job) => ["queued", "running", "stop_requested"].includes(job.status));
  const operatorBusy = all.some((job) => ["queued", "running", "stop_requested"].includes(job.status));
  const latestJob = readinessJobs.find((job) => job.result?.readiness);
  const latest = latestJob ? toRun(latestJob) : undefined;
  const active: ActiveRun | undefined = activeJob ? {
    id: activeJob.id,
    kind: activeJob.kind === "prepare" ? "prepare" : "readiness",
    pass: activeJob.kind === "prepare" ? "repair" : "check",
    label: activeJob.current_label ?? "Checking the selected lab environment.",
    startedAt: Date.parse(activeJob.started_at ?? activeJob.created_at),
    done: [],
    repairs: [],
    total: activeJob.total,
    target: [],
    announce: activeJob.status,
  } : undefined;
  const runs = readinessJobs.filter((job) => job.result?.readiness).map(toRun);
  const age = latest ? Math.max(0, now - latest.finishedAt) : 0;
  const snapshot = overviewQuery.data?.readiness;
  const fresh: Freshness = active
    ? { state: "checking", active, latest }
    : !latest
      ? { state: "never" }
      : latest.status === "BLOCKED" && snapshot?.fresh
        ? { state: "blocked", latest, age }
        : snapshot?.ready
          ? { state: "fresh", latest, age, left: Math.max(0, TTL_MS - age) }
          : { state: "stale", latest, age, reason: snapshot?.reason ?? (latest.status === "BLOCKED" ? "blocked" : "expired") };
  const scenarioState: State = { scenario: "stale", history: runs, session: [], active };
  return {
    ...scenarioState,
    runs,
    latest,
    finalMessage: "",
    now,
    fresh,
    busy: operatorBusy,
    canLaunch: fresh.state === "fresh" && !operatorBusy && !jobsQuery.isError && !overviewQuery.isError,
    error: jobsQuery.error ?? overviewQuery.error ?? undefined,
  };
}

function fromOperatorCheck(check: ReadinessCheckResult): ReadinessCheck {
  const name = check.name.toLowerCase();
  const group = name.includes("provider") || name.includes("adapter") ? "providers"
    : name.includes("repo") || name.includes("checkout") ? "repo"
      : name.includes("venv") || name.includes("python") || name.includes("pytest") ? "venv"
        : name.includes("artifact") || name.includes("path") || name.includes("disk") ? "artifacts"
          : name.includes("kubeconfig") || name.includes("lane_config") ? "kubeconfig"
            : name.includes("rag") ? "rag"
              : name.includes("pgvector") || name.includes("database") || name.includes("db_") ? "pgvector"
                : name.includes("runner") || name.includes("ground_truth") || name.includes("case_catalog") ? "static" : "live";
  const level: CheckLevel = check.status === "skip" ? "skip" : check.status === "pass" ? "pass" : check.blocking ? "block" : "warn";
  return { id: check.name, group, label: check.label, level, detail: check.detail ?? check.hint ?? "", ms: check.duration_ms ?? 0, repairable: false, commands: check.commands };
}

// ---------------------------------------------------------------- pieces

export const LEVEL_WORD: Record<CheckLevel, string> = { pass: "Passed", warn: "Warning", block: "Blocked", skip: "Skipped" };

/** Readiness marks: passes are neutral; warnings and blockers are amber. */
export function CheckMark({ level, running, pending, className }: { level?: CheckLevel; running?: boolean; pending?: boolean; className?: string }) {
  const base = clsx("size-3.5 shrink-0", className);
  if (running) return <LoaderCircle aria-label="Running" className={clsx(base, "text-accent motion-safe:animate-spin")} strokeWidth={2.25} />;
  if (pending || !level) return <Circle aria-label="Pending" className={clsx(base, "text-fg-3/60")} strokeWidth={1.75} strokeDasharray="2.5 2.5" />;
  if (level === "pass") return <Check aria-label="Passed" className={clsx(base, "text-fg-2")} strokeWidth={2.25} />;
  if (level === "warn") return <TriangleAlert aria-label="Warning" className={clsx(base, "text-warn")} strokeWidth={2} />;
  if (level === "block") return <CircleX aria-label="Blocked" className={clsx(base, "text-warn")} strokeWidth={2} />;
  return <CircleMinus aria-label="Skipped" className={clsx(base, "text-fg-3")} strokeWidth={1.75} />;
}

export function StatusWord({ fresh, className }: { fresh: Freshness; className?: string }) {
  const meta = {
    checking: { word: "Checking", dot: "bg-accent motion-safe:animate-pulse", text: "text-fg" },
    never: { word: "Not checked", dot: "border border-fg-3", text: "text-fg-3" },
    blocked: { word: "Blocked", dot: "bg-warn", text: "text-warn" },
    stale: { word: "Stale", dot: "bg-warn", text: "text-warn" },
    fresh: { word: "Ready", dot: "bg-fg", text: "text-fg" },
  }[fresh.state];
  return (
    <span className={clsx("inline-flex items-center gap-1.5 font-medium", meta.text, className)}>
      <span aria-hidden className={clsx("size-[7px] rounded-full", meta.dot)} />
      {meta.word}
    </span>
  );
}

/** One line on what the readiness state means for launching. */
export function freshnessLine(fresh: Freshness): string {
  switch (fresh.state) {
    case "checking":
      return fresh.active.label;
    case "never":
      return "No preflight on record for this lane.";
    case "blocked":
      return `Blocked ${ago(fresh.age)}. Resolve blockers, then run preflight again.`;
    case "stale": {
      const explanation = fresh.reason === "lane_changed" ? "The selected lane changed since this check."
        : fresh.reason === "operator_restarted" ? "The operator restarted since this check."
          : fresh.latest.status === "BLOCKED" ? "The last check was blocked, but it no longer describes the current lane."
            : `The last check is older than ${READINESS_TTL_MIN} minutes.`;
      return `${explanation} Run preflight again.`;
    }
    case "fresh":
      return `Ready ${ago(fresh.age)}; launches allowed until ${clockUtc(fresh.latest.finishedAt + TTL_MS)} UTC.`;
  }
}

export const clockUtc = (epoch: number) => new Date(epoch).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" });

/** Checks grouped in GROUPS order, with the worst level and summed duration. */
export function groupChecks(checks: ReadinessCheck[]) {
  return GROUPS.map((group) => {
    const list = checks.filter((c) => c.group === group.id);
    const worst: CheckLevel | undefined = list.find((c) => c.level === "block")?.level ?? list.find((c) => c.level === "warn")?.level ?? list[0]?.level;
    return { ...group, checks: list, worst, ms: list.reduce((sum, c) => sum + c.ms, 0) };
  }).filter((g) => g.checks.length);
}

/** Run preflight (check-only) and Prepare environment (repair-safe), demo jobs. */
export function RunActions({ className, size = "md" }: { className?: string; size?: "sm" | "md" }) {
  const { active, error, busy } = useFreshness();
  const queryClient = useQueryClient();
  const [actionPending, setActionPending] = useState(false);
  const [actionKind, setActionKind] = useState<"readiness" | "prepare">("readiness");
  const [actionError, setActionError] = useState("");
  const start = async (kind: "readiness" | "prepare") => {
    setActionError("");
    setActionKind(kind);
    setActionPending(true);
    try {
      await (kind === "readiness" ? readiness.run() : readiness.prepare());
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["operator-jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["operator-overview"] }),
      ]);
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "The operator action could not be started.");
    } finally {
      setActionPending(false);
    }
  };
  const btn = clsx(
    "inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-md font-medium whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-40",
    size === "sm" ? "h-7 px-2.5 text-[12.5px]" : "h-8 px-3 text-[13px]",
  );
  const demo = api.isLive ? null : <span className="font-mono text-[10px] tracking-[0.06em] uppercase opacity-60">Demo</span>;
  return (
    <div className={clsx("flex flex-wrap items-center gap-2", className)}>
      <Tip content="check_readiness.py --check-only. Reads the lane and the runner gates; changes nothing.">
        <button type="button" disabled={busy || actionPending} onClick={() => void start("readiness")} className={clsx(btn, "bg-fg text-bg hover:bg-fg/85")}>
          {actionPending && actionKind === "readiness" || active?.kind === "readiness" ? "Checking…" : "Run preflight"} {demo}
        </button>
      </Tip>
      <Tip content="check_readiness.py --repair-safe, then a check-only recheck. Repairs only this lane's own services.">
        <button type="button" disabled={busy || actionPending} onClick={() => void start("prepare")} className={clsx(btn, "border border-line-strong bg-surface text-fg hover:bg-surface-2")}>
          {actionPending && actionKind === "prepare" || active?.kind === "prepare" ? "Preparing…" : "Prepare environment"} {demo}
        </button>
      </Tip>
      {error && <p className="basis-full text-[12px] text-warn">{error.message}</p>}
      {actionError && <p role="alert" className="basis-full text-[12px] text-warn">{actionError}</p>}
    </div>
  );
}

/** What preparation may change, and what it never touches. */
export function RepairScope({ className, highlight }: { className?: string; highlight?: string[] }) {
  return (
    <div className={clsx("grid gap-2", className)}>
      <ul className="grid gap-2">
        {REPAIRS.map((r) => (
          <li key={r.name} className={clsx("grid gap-0.5 border-l-2 pl-3 text-[12.5px]", highlight?.includes(r.name) ? "border-warn" : "border-line")}>
            <span className="font-medium text-fg">{r.label}</span>
            <span className="text-fg-2">{r.does}</span>
            <span className="text-fg-3">{r.limit}</span>
          </li>
        ))}
      </ul>
      <p className="text-[12px] text-fg-3">
        Never: switching the default kubectl context, touching other profiles or researchers' containers, or falling back to shared services.
      </p>
    </div>
  );
}

/** Repairs that could clear the blocking checks in a run. */
export function repairsForRun(checks: ReadinessCheck[]): string[] {
  const failing = checks.filter((c) => c.level === "block" || c.level === "warn").map((c) => c.id);
  return REPAIRS.filter((r) => r.checks.some((id) => failing.includes(id))).map((r) => r.name);
}

export const KIND_WORD = { readiness: "Preflight", prepare: "Preparation" } as const;

/** A thin bar for the 20-minute window: full when just checked. */
export function FreshnessBar({ fresh, className }: { fresh: Freshness; className?: string }) {
  const value = fresh.state === "fresh" ? fresh.left / TTL_MS : 0;
  const progress = fresh.state === "checking" ? fresh.active.done.length / Math.max(1, fresh.active.total) : null;
  return (
    <div
      className={clsx("h-1 overflow-hidden rounded-full bg-surface-3", className)}
      role="progressbar"
      aria-label={progress !== null ? "Checks completed" : "Readiness freshness remaining"}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round((progress ?? value) * 100)}
    >
      <div
        className={clsx("h-full rounded-full transition-[width] duration-700", progress !== null ? "bg-accent" : value < 0.25 ? "bg-warn" : "bg-fg-2")}
        style={{ width: `${(progress ?? value) * 100}%` }}
      />
    </div>
  );
}

/** Demo-only control: which readiness state the lane starts in. */
export function ScenarioSwitch({ className }: { className?: string }) {
  if (api.isLive) return null;
  const { scenario } = useReadiness();
  return (
    <div className={clsx("flex flex-wrap items-center gap-2", className)}>
      <Tip content="Demo only. Sets the latest preflight on record: the real one from 19:09 (older than 20 minutes), a fresh ready result, or a blocked result with the lane's profile stopped.">
        <span tabIndex={0}>
          <Tag tone="accent">Demo</Tag>
        </span>
      </Tip>
      <Segmented<Scenario>
        label="Demo readiness state"
        value={scenario}
        onChange={readiness.setScenario}
        options={[
          { value: "stale", label: "Stale" },
          { value: "fresh", label: "Fresh" },
          { value: "blocked", label: "Blocked" },
        ]}
      />
    </div>
  );
}

/** Screen-reader announcements for streaming checks. */
export function LiveAnnouncer() {
  const { active, finalMessage: final } = useReadiness();
  return (
    <p className="sr-only" aria-live="polite" role="status">
      {active ? active.announce : final}
    </p>
  );
}

export function LaneFacts({ className, dense }: { className?: string; dense?: boolean }) {
  const rows: [string, ReactNode][] = [
    ["Profile", <span className="ident text-fg">{LANE.profile}</span>],
    ["Selector", <span className="ident">{LANE.selector}</span>],
    ["Kubeconfig", <span className="ident">{LANE.kubeconfig}</span>],
    ["RAG API", <span className="ident">{LANE.ragApi.replace("http://", "")}</span>],
    ["pgvector", <span className="ident">{LANE.pgvector}</span>],
    [
      "Default context",
      <span>
        <span className="ident line-through decoration-fg-3/60">{LANE.defaultContext}</span> <span className="text-fg-3">not used</span>
      </span>,
    ],
  ];
  return (
    <dl className={clsx("grid gap-x-4", dense ? "gap-y-1" : "gap-y-1.5", className)}>
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[104px_minmax(0,1fr)] items-baseline gap-3 text-[12.5px]">
          <dt className="text-fg-3">{label}</dt>
          <dd className="min-w-0 text-fg-2 [overflow-wrap:anywhere]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export { GROUPS, LANE, READINESS_TTL_MIN, READY_CHECKS, BLOCKED_CHECKS, summarize };
export type { CheckLevel, ReadinessCheck };
