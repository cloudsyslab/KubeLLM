// Demo readiness results for the Environment, New campaign, and Jobs options.
// Group names follow the benchmark skill's check_readiness.py; the runner live
// gate's check names are the real ones from debug_assistant_latest/preflight.py.
// Messages are representative, not captured output. Tag every view as Demo.

export const LANE = {
  id: "minh",
  profile: "minh-lane",
  selector: "~/.config/kubellm/lanes/minh.json",
  kubeconfig: "~/.config/kubellm/lanes/minh.kubeconfig",
  serviceEnv: "~/.config/kubellm/lanes/minh.env",
  ragApi: "http://127.0.0.1:18004",
  pgvector: "kubellm-minh-lane-pgvector",
  defaultContext: "minikube",
};

/** Readiness stays fresh for 20 minutes, as in operator_ui/app.py. */
export const READINESS_TTL_MIN = 20;

export type CheckLevel = "pass" | "warn" | "block" | "skip";

export interface ReadinessCheck {
  id: string;
  group: string;
  label: string;
  level: CheckLevel;
  detail: string;
  ms: number;
  /** Preparation (repair-safe mode) may fix this check. */
  repairable?: boolean;
}

export const GROUPS = [
  { id: "repo", label: "Repository" },
  { id: "venv", label: "Python environment" },
  { id: "providers", label: "Provider adapters" },
  { id: "artifacts", label: "Artifact paths" },
  { id: "kubeconfig", label: "Lane kubeconfig" },
  { id: "rag", label: "RAG service" },
  { id: "pgvector", label: "pgvector" },
  { id: "static", label: "Runner static gates" },
  { id: "live", label: "Runner live gates" },
] as const;

export const READY_CHECKS: ReadinessCheck[] = [
  { id: "repo_checkout", group: "repo", label: "Checkout", level: "pass", detail: "KubeLLM checkout found; runner entry point present.", ms: 140 },
  { id: "venv_python", group: "venv", label: "Interpreter", level: "pass", detail: ".venv Python 3.10 resolves the runner's requirements.", ms: 620 },
  { id: "providers_api", group: "providers", label: "API provider", level: "pass", detail: "OpenAI credentials present (value hidden).", ms: 210 },
  { id: "providers_ollama", group: "providers", label: "Ollama", level: "pass", detail: "Ollama reachable at 127.0.0.1:11434; required local models are present.", ms: 380 },
  { id: "artifacts_paths", group: "artifacts", label: "Run output paths", level: "pass", detail: "Run roots under .local/ are writable and outside Git.", ms: 90 },
  { id: "artifacts_disk", group: "artifacts", label: "Docker data root", level: "warn", detail: "About 12 GB free. Starting the lane's profile needs 20 GiB, so preparation could not restart the lane.", ms: 160 },
  { id: "kubeconfig_owner", group: "kubeconfig", label: "Owner-only kubeconfig", level: "pass", detail: "Lane kubeconfig is owner-only and targets minh-lane.", ms: 70 },
  { id: "rag_lane", group: "rag", label: "Lane RAG API", level: "pass", detail: "RAG API reachable at 127.0.0.1:18004 and bound to lane minh.", ms: 440, repairable: true },
  { id: "pgvector_owner", group: "pgvector", label: "Lane pgvector", level: "pass", detail: "kubellm-minh-lane-pgvector is running and owned by this lane.", ms: 310, repairable: true },
  { id: "static_list", group: "static", label: "runner.py --list", level: "pass", detail: "27 cases discovered.", ms: 1840 },
  { id: "static_truth", group: "static", label: "runner.py --validate-ground-truth", level: "pass", detail: "Ground Truth definitions valid for all 27 cases.", ms: 2210 },
  { id: "python_imports", group: "live", label: "python_imports", level: "pass", detail: "Required Python packages import.", ms: 510 },
  { id: "pytest", group: "live", label: "pytest", level: "pass", detail: "pytest is available.", ms: 230 },
  { id: "db_connectivity", group: "live", label: "db_connectivity", level: "pass", detail: "Connected to the configured database.", ms: 260 },
  { id: "rag_api", group: "live", label: "rag_api", level: "pass", detail: "RAG API reachable and matches the selected lab lane.", ms: 300 },
  { id: "lab_lane", group: "live", label: "lab_lane", level: "pass", detail: "Profile, kubeconfig, pgvector owner, and endpoint match the selected lane.", ms: 190 },
  { id: "kubectl", group: "live", label: "kubectl", level: "pass", detail: "kubectl is available.", ms: 160 },
  { id: "docker_engine", group: "live", label: "docker_engine", level: "pass", detail: "Docker engine is available.", ms: 280 },
  { id: "minikube_status", group: "live", label: "minikube_status", level: "pass", detail: "minikube profile 'minh-lane' is healthy.", ms: 1350, repairable: true },
  { id: "cluster_access", group: "live", label: "cluster_access", level: "pass", detail: "kubectl get nodes succeeded.", ms: 640 },
  { id: "config_validity", group: "live", label: "config_validity", level: "pass", detail: "Case configurations are valid.", ms: 720 },
];

/** An earlier blocked result: the lane's profile was down. */
export const BLOCKED_CHECKS: ReadinessCheck[] = READY_CHECKS.map((check) =>
  check.id === "minikube_status"
    ? { ...check, level: "block", detail: "minikube profile 'minh-lane' is unhealthy: host is Stopped." }
    : check.id === "cluster_access"
      ? { ...check, level: "block", detail: "kubectl get nodes failed: the connection to the server was refused." }
      : check.id === "rag_lane" || check.id === "rag_api"
        ? { ...check, level: "block", detail: "RAG API did not answer at 127.0.0.1:18004." }
        : check,
);

export function summarize(checks: ReadinessCheck[]) {
  const count = (level: CheckLevel) => checks.filter((c) => c.level === level).length;
  const blocked = count("block");
  return { status: blocked ? ("BLOCKED" as const) : ("READY" as const), pass: count("pass"), warn: count("warn"), block: blocked, skip: count("skip"), ms: checks.reduce((sum, c) => sum + c.ms, 0) };
}
