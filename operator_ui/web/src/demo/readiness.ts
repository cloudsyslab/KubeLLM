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

/** September results, before the Docker data root filled up. */
export const EARLIER_READY_CHECKS: ReadinessCheck[] = READY_CHECKS.map((check) =>
  check.id === "artifacts_disk" ? { ...check, level: "pass", detail: "Docker data root has at least 20 GiB free." } : check,
);

/** An earlier blocked result: the lane's profile was down. */
export const BLOCKED_CHECKS: ReadinessCheck[] = EARLIER_READY_CHECKS.map((check) =>
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

// ---------------------------------------------------------------- executions
//
// What each check ran: the processes check_readiness.py and runner.py
// --preflight start for it, with their output streams and exit codes. The
// commands follow the real scripts; the output is representative, elided where
// long, and redacted. Tag every view as Demo.

/** One process a check ran. */
export interface CheckCommand {
  cmd: string;
  stdout?: string[];
  stderr?: string[];
  /** Absent for a process left running in the background. */
  exit?: number;
}

export interface CheckExecution {
  /** The command this check runs inside, when one command reports several checks. */
  via?: string;
  /** How to read these lines (in-process checks, HTTP probes, elided output). */
  note?: string;
  commands: CheckCommand[];
  /** What the check itself reports after its commands (preflight's JSON entry, in-process reads). */
  result?: { stdout?: string[]; stderr?: string[] };
}

const PY = ".venv/bin/python";
const RUNNER = `${PY} debug_assistant_latest/runner.py --lab-config ${LANE.selector}`;
const RAG_HOST = LANE.ragApi.replace("http://", "");
/** The lane node's API server, as the topology demo names it. */
const API_SERVER = "192.168.49.2:8443";
const HTTP_NOTE = "HTTP probes are shown as curl equivalents; the script sends them with urllib.";
const PREFLIGHT_NOTE = "runner.py --preflight runs every live gate in one process and prints one JSON report; these are this gate's lines.";
const entry = (name: string, passed: boolean, message: string) => JSON.stringify({ name, passed, message });
const live = (name: string, passed: boolean, message: string, commands: CheckCommand[] = []): CheckExecution => ({
  via: `${RUNNER} --preflight`,
  note: PREFLIGHT_NOTE,
  commands,
  result: { stdout: [entry(name, passed, message)] },
});

const EXECUTIONS: Record<string, (level: CheckLevel) => CheckExecution> = {
  repo_checkout: () => ({
    commands: [
      { cmd: "git rev-parse --show-toplevel", stdout: ["~/KubeLLM"], exit: 0 },
      { cmd: "git remote get-url origin", stdout: ["https://github.com/cloudsyslab/KubeLLM.git"], exit: 0 },
      { cmd: "git branch --show-current", stdout: ["minh"], exit: 0 },
      { cmd: "git status --porcelain=v1 --untracked-files=all", exit: 0 },
    ],
  }),
  venv_python: () => ({
    note: "The package list is elided.",
    commands: [
      { cmd: `${PY} -m pip list --format=json`, stdout: ['[{"name": "aiohappyeyeballs", "version": "…"}, …]'], exit: 0 },
      { cmd: `${PY} -m pip check`, stdout: ["No broken requirements found."], exit: 0 },
    ],
  }),
  providers_api: () => ({
    note: HTTP_NOTE,
    commands: ["gpt-5-mini", "gpt-5-nano"].map((model) => ({
      cmd: `curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer [redacted]" https://api.openai.com/v1/models/${model}`,
      stdout: ["200"],
      exit: 0,
    })),
  }),
  providers_ollama: () => ({
    note: HTTP_NOTE,
    commands: [{ cmd: `curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:11434/api/show -d '{"model": "glm-4.7-flash:latest"}'`, stdout: ["200"], exit: 0 }],
  }),
  artifacts_paths: () => ({
    note: "Checked in process with os.access; no command runs.",
    commands: [],
    result: { stdout: [".local/readiness  writable_or_creatable_without_check_only_writes", ".local/services  writable_or_creatable_without_check_only_writes", ".local/runs  writable_or_creatable_without_check_only_writes"] },
  }),
  artifacts_disk: (level) => ({
    note: "Free space is read in process with shutil.disk_usage.",
    commands: [{ cmd: "docker info --format {{.DockerRootDir}}", stdout: ["/var/lib/docker"], exit: 0 }],
    result: { stdout: [level === "warn" ? "free: 11.2 GiB" : "free: at least 20 GiB"] },
  }),
  kubeconfig_owner: () => ({
    note: "File modes are checked in process; certificate data is redacted.",
    commands: [
      {
        cmd: `kubectl --kubeconfig ${LANE.kubeconfig} config view --raw --minify --flatten -o json`,
        stdout: [`{"clusters": [{"cluster": {"certificate-authority-data": "[redacted]", "server": "https://${API_SERVER}"}, "name": "${LANE.profile}"}], "users": [{"user": {"client-certificate-data": "[redacted]", "client-key-data": "[redacted]"}}], …}`],
        exit: 0,
      },
      { cmd: `kubectl --kubeconfig ${LANE.kubeconfig} get nodes --request-timeout=10s -o name`, stdout: [`node/${LANE.profile}`], exit: 0 },
    ],
    result: { stdout: ["kubeconfig 0600 · directory 0700 · owner only"] },
  }),
  rag_lane: (level) => ({
    note: HTTP_NOTE,
    commands: [
      level === "block"
        ? { cmd: `curl -s ${LANE.ragApi}/server_info/`, stderr: [`curl: (7) Failed to connect to 127.0.0.1 port ${RAG_HOST.split(":")[1]} after 0 ms: Couldn't connect to server`], exit: 7 }
        : { cmd: `curl -s ${LANE.ragApi}/server_info/`, stdout: [`{"api_version": "…", "repo_signature": "…", "server_port": ${RAG_HOST.split(":")[1]}, "server_bind_host": "127.0.0.1", "database_identity": "…"}`], exit: 0 },
    ],
  }),
  pgvector_owner: () => ({
    note: "Long JSON output is elided.",
    commands: [{ cmd: `docker inspect ${LANE.pgvector} --format '{{json .}}'`, stdout: [`{"Name": "/${LANE.pgvector}", "State": {"Running": true, …}, "Config": {"Labels": {"io.kubellm.lane": "${LANE.id}", …}, …}, …}`], exit: 0 }],
  }),
  static_list: () => ({
    note: "The case list is elided after three.",
    commands: [{ cmd: `${RUNNER} --list`, stdout: ["Available test cases (27):", "  environment_variable", "  environment_variable_wrong_name", "  incorrect_selector", "  …"], exit: 0 }],
  }),
  static_truth: () => ({
    commands: [{ cmd: `${RUNNER} --validate-ground-truth`, stdout: ["Validation PASSED"], exit: 0 }],
  }),
  python_imports: () => live("python_imports", true, "Imported runtime modules: main, report, ground_truth"),
  pytest: () => live("pytest", true, "pytest is available"),
  db_connectivity: () => live("db_connectivity", true, "Connected to the configured database"),
  rag_api: (level) =>
    level === "block"
      ? live("rag_api", false, `RAG API check failed for ${LANE.ragApi}/server_info/: connection refused`)
      : live("rag_api", true, `RAG API reachable at ${LANE.ragApi}/server_info/ (api_version=…)`),
  lab_lane: () => live("lab_lane", true, "Profile, kubeconfig, pgvector owner, and endpoint match the selected lane"),
  kubectl: () => live("kubectl", true, "kubectl is available", [{ cmd: "kubectl version --client --output=json", stdout: ['{"clientVersion": {"major": "1", "minor": "31", "gitVersion": "v1.31.0", …}}'], exit: 0 }]),
  docker_engine: () => live("docker_engine", true, "Docker engine is available", [{ cmd: "docker version", stdout: ["Client: Docker Engine - Community", "Server: Docker Engine - Community"], exit: 0 }]),
  minikube_status: (level) =>
    level === "block"
      ? live("minikube_status", false, `minikube profile '${LANE.profile}' is unhealthy: host: Stopped`, [
          { cmd: `minikube status -p ${LANE.profile}`, stdout: [LANE.profile, "type: Control Plane", "host: Stopped", "kubelet: Stopped", "apiserver: Stopped", "kubeconfig: Stopped"], exit: 7 },
        ])
      : live("minikube_status", true, `minikube profile '${LANE.profile}' is healthy`, [
          { cmd: `minikube status -p ${LANE.profile}`, stdout: [LANE.profile, "type: Control Plane", "host: Running", "kubelet: Running", "apiserver: Running", "kubeconfig: Configured"], exit: 0 },
        ]),
  cluster_access: (level) =>
    level === "block"
      ? live("cluster_access", false, `kubectl get nodes failed: The connection to the server ${API_SERVER} was refused - did you specify the right host or port?`, [
          { cmd: "kubectl get nodes", stderr: [`The connection to the server ${API_SERVER} was refused - did you specify the right host or port?`], exit: 1 },
        ])
      : live("cluster_access", true, "kubectl get nodes succeeded", [{ cmd: "kubectl get nodes", stdout: ["NAME STATUS ROLES AGE VERSION", `${LANE.profile} Ready control-plane 34d v1.31.0`], exit: 0 }]),
  config_validity: () => live("config_validity", true, "Validated 27 config(s)"),
};

/** The processes a check ran and what they printed, for its terminal view. */
export function executionOf(check: ReadinessCheck): CheckExecution {
  return EXECUTIONS[check.id]?.(check.level) ?? { commands: [], note: "No command is recorded for this check." };
}
