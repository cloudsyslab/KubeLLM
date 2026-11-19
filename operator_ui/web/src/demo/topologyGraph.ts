import { FAILURE_ATTEMPT, SERVICE_NAMES, type DemoAttempt, type DemoCampaign, type DemoPhase } from "./campaign";
import { HOST, processesAt, sampleAt } from "./lab";
import { LANE, READY_CHECKS, type ReadinessCheck } from "./readiness";
import { topologyAt, type Pod } from "./topology";

// A typed dependency graph of the lab, derived from the simulated inventory in
// topology.ts and the host telemetry in lab.ts at replay time t. Nodes are only
// what the 2026-11-01 survey supports plus the case fixture's own generic
// Kubernetes objects. Everything here is Demo state.
//
// Health is an operator judgment, never a Ground Truth outcome: expected broken
// fixtures and known leftovers are explained, and never degrade the lane.

export type Health = "healthy" | "degraded" | "failing" | "expected-broken" | "leftover" | "stopped" | "unknown";

export const HEALTH: Record<Health, { word: string; rank: number; attention?: boolean; explained?: boolean }> = {
  failing: { word: "Failing", rank: 0, attention: true },
  degraded: { word: "Degraded", rank: 1, attention: true },
  unknown: { word: "Unknown", rank: 2 },
  stopped: { word: "Stopped", rank: 3 },
  leftover: { word: "Leftover", rank: 4, explained: true },
  "expected-broken": { word: "Expected broken", rank: 5, explained: true },
  healthy: { word: "Healthy", rank: 6 },
};
export const HEALTH_ORDER = Object.keys(HEALTH).sort((a, b) => HEALTH[a as Health].rank - HEALTH[b as Health].rank) as Health[];

export type NodeKind = "host" | "gpu" | "runtime" | "container" | "process" | "external" | "profile" | "k8s-node" | "namespace" | "pod" | "service" | "endpoints";
export type Scope = "lane" | "shared" | "other" | "external";
export type NodeTag = "selected-lane" | "default-context" | "fixture" | "leftover" | "system" | "read-only";

export interface Fact {
  label: string;
  value: string;
}

export interface TopoNode {
  id: string;
  kind: NodeKind;
  kindLabel: string;
  name: string;
  /** Address, container name, or other identifier, shown in mono. */
  ident?: string;
  /** Containment or runs-on parent: what this node is summarized under. */
  parent?: string;
  health: Health;
  /** Short categorical status, e.g. "CrashLoopBackOff · 0/1" or "Serving retrieval". */
  status: string;
  /** Why it has this health, in operator language. */
  reason: string;
  scope: Scope;
  tags: NodeTag[];
  facts: Fact[];
  /** Carrying traffic for the current campaign phase. */
  active: boolean;
}

export type EdgeKind = "contains" | "runs-on" | "depends-on" | "serves" | "routes-to";

export const EDGE_KIND: Record<EdgeKind, { word: string; hint: string }> = {
  "depends-on": { word: "Calls", hint: "The source calls the target and needs it." },
  serves: { word: "Serves", hint: "The source serves models or retrieval to the target." },
  "routes-to": { word: "Routes to", hint: "Service traffic flows to Endpoints, then to the pod." },
  "runs-on": { word: "Runs on", hint: "The source runs on the target and stops with it." },
  contains: { word: "Contains", hint: "The target lives inside the source." },
};

export interface TopoEdge {
  id: string;
  kind: EdgeKind;
  source: string;
  target: string;
  label: string;
  /** Losing the dependency takes the dependent down (hard) or only impairs it. */
  hard: boolean;
  /** The dependent's effect is a benchmark outcome, not a lab fault. */
  outcome?: boolean;
  /** What happens to the dependent if the dependency fails. */
  impact: string;
  active: boolean;
  /** Present in the manifest but not carrying anything, e.g. a selector that matches no pod. */
  broken?: boolean;
}

export interface Rollup {
  health: Health;
  reason: string;
  /** Own health of every descendant. */
  counts: Record<Health, number>;
  total: number;
  attention: string[];
  explained: string[];
}

export interface TopologyGraph {
  t: number;
  nodes: TopoNode[];
  edges: TopoEdge[];
  byId: Map<string, TopoNode>;
  children: Map<string, string[]>;
  rollups: Map<string, Rollup>;
  attempt?: DemoAttempt;
  phase?: DemoPhase;
  campaignStatus: "running" | "completed" | "failed";
  /** Request paths for the current phase, in call order (caller first). */
  traffic: { label: string; paths: string[][] };
  lane: Rollup;
  /** False when the source exposes inventory and containment, but no dependencies. */
  relationshipsKnown?: boolean;
}

/** The lane's own pieces: its profile, its services, and the worker driving it. */
export const LANE_MEMBERS = ["profile:minh-lane", "rag", "pgvector", "worker"];

// Only these demo cases ship a Service next to the pod
// (debug_assistant_latest/troubleshooting/<case>/app_service.yaml); the rest
// deploy a bare Pod.
const SERVICE_CASES: Record<string, { endpoints: number; broken: string }> = {
  incorrect_selector: { endpoints: 0, broken: "Its selector matches no pod, so it has no endpoints." },
  port_mismatch_named_target: { endpoints: 1, broken: "Its targetPort doesn't name the container's port, so requests don't reach the app." },
  wrong_interface_bind_address: { endpoints: 1, broken: "Endpoints are listed, but the app listens on 127.0.0.1, so requests time out." },
};

const SYSTEM_ROLES: Record<string, string> = {
  coredns: "Cluster DNS.",
  etcd: "Stores the lane's cluster state.",
  "kube-apiserver": "Serves the Kubernetes API that kubectl and the worker call.",
  "kube-controller-manager": "Reconciles cluster objects.",
  "kube-proxy": "Programs Service routing on the node.",
  "kube-scheduler": "Places pods on the node.",
  "storage-provisioner": "minikube's hostPath volume provisioner.",
};

/** Readiness checks (readiness.ts) that fail when a node is down or impaired. */
const CHECKS_BY_NODE: Record<string, string[]> = {
  docker: ["docker_engine"],
  "profile:minh-lane": ["minikube_status", "cluster_access", "lab_lane"],
  "node:minh-lane": ["cluster_access"],
  "sys:kube-apiserver": ["cluster_access"],
  rag: ["rag_lane", "rag_api"],
  pgvector: ["pgvector_owner", "lab_lane"],
  ollama: ["providers_ollama"],
};

export const isLocalModel = (model?: string) => !!model && model.includes(":");
const systemId = (podName: string) => `sys:${Object.keys(SYSTEM_ROLES).find((role) => podName.startsWith(role)) ?? podName}`;
// Same addressing as the demo campaign's simulated output.
const podIp = (index: number) => `10.244.0.${20 + index}`;
const apiModelFor = (phaseKey: string | undefined, model: string | undefined) =>
  phaseKey === "knowledge" ? "gpt-5-mini" : phaseKey === "verify" ? "gpt-5-nano" : phaseKey === "debug" && !isLocalModel(model) ? (model ?? "API model") : "API models";

function fixtureState(pod: Pod, attempt: DemoAttempt, phase: DemoPhase, failing: boolean): { health: Health; reason: string } {
  if (failing) return { health: "failing", reason: pod.note ?? "Setup error." };
  if (phase.key === "setup") return { health: "expected-broken", reason: "Being created by setup. Broken by design until the debug agent repairs it." };
  if (phase.key === "teardown") return { health: "stopped", reason: pod.note ?? "Teardown is removing it." };
  const checked = phase.key === "verify" || phase.key === "truth";
  if (checked && attempt.outcome === "pass") return { health: "healthy", reason: "Repaired by the debug agent. Ground Truth decides the attempt's outcome." };
  if (checked) return { health: "expected-broken", reason: "Still broken after the agent's fix. Ground Truth records that as the attempt's outcome; it isn't a lab fault." };
  return { health: "expected-broken", reason: `Broken by design: ${(pod.note ?? "").replace(/^Expected: /, "")}` };
}

export function graphAt(campaign: DemoCampaign, t: number): TopologyGraph {
  const topo = topologyAt(campaign, t);
  const laneProfile = topo.profiles.find((p) => p.selected)!;
  const attempt = campaign.attempts.find((a) => t >= a.start && t < a.end);
  const phase = attempt?.phases.find((p) => t >= p.start && t < p.end);
  const last = campaign.attempts[campaign.attempts.length - 1];
  const campaignStatus: TopologyGraph["campaignStatus"] = campaign.failure && last && t >= last.end ? "failed" : t >= campaign.total ? "completed" : "running";
  const failing = !!attempt && campaign.failure && attempt.index === FAILURE_ATTEMPT;
  const local = isLocalModel(attempt?.model);
  const key = phase?.key;
  const sample = sampleAt(campaign, t);
  const procs = processesAt(campaign, t);
  const ollamaProc = procs.find((p) => p.name === "ollama");
  const otherProc = procs.find((p) => p.attribution === "other");
  const loaded = !!ollamaProc;
  const localDebug = key === "debug" && local;

  const nodes: TopoNode[] = [];
  const edges: TopoEdge[] = [];
  const add = (node: Omit<TopoNode, "tags" | "facts" | "active"> & Partial<Pick<TopoNode, "tags" | "facts">>) => nodes.push({ tags: [], facts: [], active: false, ...node });
  const link = (kind: EdgeKind, source: string, target: string, label: string, impact: string, hard: boolean, extra: Partial<TopoEdge> = {}) =>
    edges.push({ id: `${kind}:${source}>${target}`, kind, source, target, label, impact, hard, active: false, ...extra });

  // Host and devices
  add({
    id: "host",
    kind: "host",
    kindLabel: "Lab host",
    name: HOST.name,
    ident: "Ubuntu 22.04",
    health: "degraded",
    status: "Up · root disk 98%",
    reason: `Root disk is 98% used (about ${HOST.diskFreeGB} GB free). Running work is unaffected, but a stopped lane couldn't be restarted: starting a profile needs 20 GiB on the Docker data root.`,
    scope: "shared",
    facts: [
      { label: "OS", value: "Ubuntu 22.04" },
      { label: "Threads", value: String(HOST.threads) },
      { label: "Memory", value: `${sample.memUsedGiB.toFixed(1)} of ${HOST.memTotalGiB} GiB used` },
      { label: "Root disk", value: `${HOST.diskUsedGB} GB used · about ${HOST.diskFreeGB} GB free` },
      { label: "GPUs", value: "2× NVIDIA A40 · 46 GB" },
    ],
  });
  const g0 = sample.gpus[0];
  add({
    id: "gpu-0",
    kind: "gpu",
    kindLabel: "GPU",
    name: "GPU 0",
    ident: "NVIDIA A40",
    parent: "host",
    health: "healthy",
    status: localDebug ? "Busy" : loaded ? "Model loaded" : "Idle",
    reason: localDebug
      ? "Running Ollama's glm-4.7-flash. The load coincides with this attempt's debug phase; Ollama is shared, so it isn't attributed to the run."
      : loaded
        ? "Ollama keeps glm-4.7-flash loaded for its keep-alive window after the last local-model call."
        : "Idle. Ollama loads the local model here when a glm-4.7-flash attempt reaches its debug phase.",
    scope: "shared",
    facts: [
      { label: "Utilization", value: `${Math.round(g0.util * 100)}%` },
      { label: "VRAM", value: `${g0.vramGB.toFixed(1)} of 46 GB` },
      { label: "Temperature", value: `${Math.round(g0.tempC)} °C` },
      { label: "Process", value: loaded ? "ollama (root, shared)" : "None" },
    ],
  });
  const g1 = sample.gpus[1];
  add({
    id: "gpu-1",
    kind: "gpu",
    kindLabel: "GPU",
    name: "GPU 1",
    ident: "NVIDIA A40",
    parent: "host",
    health: "healthy",
    status: otherProc ? "Busy · other account" : "Idle",
    reason: otherProc
      ? "Another account's process. Its load is unrelated to KubeLLM and isn't attributed to the campaign."
      : "Idle. Another account runs jobs here on its own schedule; KubeLLM doesn't use this GPU.",
    scope: "other",
    facts: [
      { label: "Utilization", value: `${Math.round(g1.util * 100)}%` },
      { label: "VRAM", value: `${g1.vramGB.toFixed(1)} of 46 GB` },
      { label: "Process", value: otherProc ? "Another account's python3" : "None" },
    ],
  });

  // Runtime and lane services
  add({
    id: "docker",
    kind: "runtime",
    kindLabel: "Container runtime",
    name: "Docker daemon",
    ident: "dockerd",
    parent: "host",
    health: "degraded",
    status: "Running · data root low",
    reason: `About ${HOST.diskFreeGB} GB free on the Docker data root. Running containers are unaffected, but starting a minikube profile needs 20 GiB (preflight warns on the Docker data root).`,
    scope: "shared",
    facts: [
      { label: "Data root free", value: `About ${HOST.diskFreeGB} GB · 20 GiB needed to start a profile` },
      { label: "Profiles", value: "5 minikube · 1 running" },
      { label: "Lane containers", value: `minh-lane, ${LANE.pgvector}` },
    ],
  });
  add({
    id: "pgvector",
    kind: "container",
    kindLabel: "Lane service",
    name: "pgvector",
    ident: LANE.pgvector,
    parent: "docker",
    health: "healthy",
    status: key === "knowledge" ? "Serving queries" : "Idle",
    reason: "Running and owned by lane minh (preflight: Lane pgvector).",
    scope: "lane",
    facts: [
      { label: "Container", value: LANE.pgvector },
      { label: "Owner", value: "Lane minh" },
      { label: "Up", value: "5 weeks" },
    ],
  });
  add({
    id: "rag",
    kind: "process",
    kindLabel: "Lane service",
    name: "RAG API",
    ident: "127.0.0.1:18004",
    parent: "host",
    health: "healthy",
    status: key === "knowledge" ? "Serving retrieval" : "Idle",
    reason: "Reachable and bound to lane minh (preflight: Lane RAG API).",
    scope: "lane",
    facts: [
      { label: "Address", value: "127.0.0.1:18004" },
      { label: "Lane", value: "minh" },
      { label: "Process", value: "python3 · pid 1493494" },
      { label: "Up", value: "34 days" },
    ],
  });
  add({
    id: "ollama",
    kind: "process",
    kindLabel: "Model server",
    name: "Ollama",
    ident: "127.0.0.1:11434",
    parent: "host",
    health: "healthy",
    status: localDebug ? "Serving glm-4.7-flash" : loaded ? "glm-4.7-flash loaded" : "Idle",
    reason: "Shared by the lab's accounts. Serves the local debug model from GPU 0 when a glm-4.7-flash attempt runs.",
    scope: "shared",
    facts: [
      { label: "Address", value: "127.0.0.1:11434" },
      { label: "Models", value: "9 local" },
      { label: "Loaded", value: loaded ? `glm-4.7-flash · ${(g0.vramGB - 0.5).toFixed(1)} GB on GPU 0` : "None" },
      { label: "Owner", value: "root · shared" },
    ],
  });
  add({
    id: "openai",
    kind: "external",
    kindLabel: "External API",
    name: "OpenAI API",
    health: "healthy",
    status: phase && (key === "knowledge" || key === "verify" || (key === "debug" && !local)) ? `In use · ${apiModelFor(key, attempt?.model)}` : "Idle",
    reason: "Calls in this campaign succeed. Preflight confirms credentials exist, not that the API is up.",
    scope: "external",
    facts: [
      { label: "Knowledge", value: "gpt-5-mini" },
      { label: "Verifier", value: "gpt-5-nano" },
      { label: "Debug", value: "gpt-6-luna" },
      { label: "Credentials", value: "Present (value hidden)" },
    ],
  });
  add({
    id: "operator",
    kind: "process",
    kindLabel: "Operator app",
    name: "Operator app",
    ident: "127.0.0.1:8787",
    parent: "host",
    health: "healthy",
    status: "Serving",
    reason: "Serves this UI and reads the worker's job state. Anyone on the lab or VPN network can reach it.",
    scope: "lane",
    facts: [
      { label: "Process", value: "uvicorn · pid 4086235" },
      { label: "Address", value: "127.0.0.1:8787" },
    ],
  });

  const workerState: Pick<TopoNode, "health" | "status" | "reason"> =
    campaignStatus === "failed"
      ? { health: "stopped", status: "Stopped on error", reason: `The campaign stopped on a runner error in attempt ${FAILURE_ATTEMPT + 1}; teardown completed. Runner errors don't count against the model.` }
      : failing
        ? { health: "failing", status: "Runner error", reason: "Setup failed: the fixture image is missing (ErrImagePull). Teardown runs, then the campaign stops. Not counted against the model." }
        : campaignStatus === "completed"
          ? { health: "healthy", status: "Idle · campaign done", reason: "The campaign completed; every attempt's teardown restored the lane's baseline." }
          : attempt && phase
            ? { health: "healthy", status: `Attempt ${attempt.index + 1} · ${phase.label}`, reason: `Running the campaign serially on ${LANE.profile}.` }
            : { health: "healthy", status: "Between attempts", reason: `Running the campaign serially on ${LANE.profile}.` };
  add({
    id: "worker",
    kind: "process",
    kindLabel: "Benchmark worker",
    name: "KubeLLM worker",
    ident: "runner.py",
    parent: "host",
    ...workerState,
    scope: "lane",
    facts: [
      { label: "Process", value: "python3 · pid 2214907" },
      { label: "Lane", value: `${LANE.profile} via ${LANE.selector}` },
      { label: "Execution", value: "Serial" },
      ...(attempt ? [{ label: "Attempt", value: `${attempt.index + 1} · ${attempt.model.replace(/:latest$/, "")} · ${attempt.caseId}` }] : []),
    ],
  });

  // Profiles
  for (const profile of topo.profiles) {
    const id = `profile:${profile.name}`;
    add({
      id,
      kind: "profile",
      kindLabel: "minikube profile",
      name: profile.name,
      parent: "docker",
      health: profile.status === "Running" ? "healthy" : profile.status === "Stopped" ? "stopped" : "unknown",
      status: profile.status,
      reason: profile.selected
        ? "Selected private lane. Actions are confined to it, through its own kubeconfig."
        : profile.defaultContext
          ? "Stopped. It's the default kubectl context, which KubeLLM never uses to pick a target."
          : "minikube reports Unknown. Read-only: its workloads aren't queried.",
      scope: profile.selected ? "lane" : "other",
      tags: profile.selected ? ["selected-lane"] : profile.defaultContext ? ["default-context", "read-only"] : ["read-only"],
      facts: [
        { label: "Kubernetes", value: profile.kubernetes },
        { label: "Driver", value: profile.driver },
        { label: "Access", value: profile.selected ? "Selected lane: actions allowed" : "Read-only status" },
        ...(profile.selected ? [{ label: "Kubeconfig", value: LANE.kubeconfig }] : []),
      ],
    });
    link("runs-on", id, "docker", "runs on", "Its minikube container stops with Docker.", true);
  }

  // The lane's cluster
  const k8sNode = laneProfile.nodes[0];
  add({
    id: "node:minh-lane",
    kind: "k8s-node",
    kindLabel: "Node",
    name: k8sNode.name,
    ident: k8sNode.ip,
    parent: "profile:minh-lane",
    health: "healthy",
    status: k8sNode.status,
    reason: "Ready. Single-node cluster: every lane pod runs here.",
    scope: "lane",
    facts: [
      { label: "Internal IP", value: k8sNode.ip ?? "—" },
      { label: "Kubernetes", value: laneProfile.kubernetes },
    ],
  });
  link("contains", "profile:minh-lane", "node:minh-lane", "contains", "The node goes down with its profile.", true);
  for (const ns of ["default", "kube-system"]) {
    const pods = laneProfile.pods.filter((p) => p.namespace === ns);
    add({
      id: `ns:${ns}`,
      kind: "namespace",
      kindLabel: "Namespace",
      name: ns,
      parent: "profile:minh-lane",
      health: "healthy",
      status: "Active",
      reason: ns === "default" ? "Where case fixtures are deployed. Also holds two known leftovers." : "The lane's cluster components.",
      scope: "lane",
      facts: [{ label: "Pods", value: String(pods.length) }],
    });
    link("contains", "profile:minh-lane", `ns:${ns}`, "contains", "The namespace goes down with its profile.", true);
  }

  const fixture = laneProfile.pods.find((p) => p.kind === "fixture");
  if (fixture && attempt && phase) {
    const state = fixtureState(fixture, attempt, phase, failing);
    add({
      id: "fixture:pod",
      kind: "pod",
      kindLabel: "Pod · fixture",
      name: fixture.name,
      parent: "ns:default",
      ...state,
      status: `${fixture.status} · ${fixture.ready}`,
      scope: "lane",
      tags: ["fixture"],
      facts: [
        { label: "Case", value: attempt.caseId },
        { label: "Attempt", value: `${attempt.index + 1} · ${attempt.model.replace(/:latest$/, "")}` },
        { label: "Ready", value: fixture.ready },
        { label: "Restarts", value: String(fixture.restarts) },
        { label: "Pod IP", value: podIp(attempt.index) },
        { label: "Age", value: fixture.age },
      ],
    });
    const svc = SERVICE_CASES[attempt.caseId];
    if (svc && !failing) {
      const name = SERVICE_NAMES[attempt.caseId] ?? `${fixture.name}-svc`;
      const repaired = state.health === "healthy";
      const gone = phase.key === "teardown";
      const svcState: Pick<TopoNode, "health" | "status" | "reason"> = gone
        ? { health: "stopped", status: "Terminating", reason: "Scoped teardown is removing this case's resources." }
        : repaired
          ? { health: "healthy", status: "Routing", reason: "Repaired with the pod. Ground Truth decides the attempt's outcome." }
          : { health: "expected-broken", status: svc.endpoints ? "Not reaching the app" : "No endpoints", reason: `Broken by design. ${svc.broken}` };
      add({ id: "fixture:svc", kind: "service", kindLabel: "Service · fixture", name, parent: "ns:default", ...svcState, scope: "lane", tags: ["fixture"], facts: [{ label: "Case", value: attempt.caseId }, { label: "Selects", value: svc.endpoints || repaired ? `app=${fixture.name}` : "No matching pod" }] });
      const addresses = repaired ? 1 : svc.endpoints;
      add({
        id: "fixture:ep",
        kind: "endpoints",
        kindLabel: "Endpoints · fixture",
        name,
        parent: "ns:default",
        health: gone ? "stopped" : addresses ? "healthy" : "expected-broken",
        status: gone ? "Terminating" : `${addresses} ${addresses === 1 ? "address" : "addresses"}`,
        reason: gone ? "Removed with its Service." : addresses ? `Lists the fixture pod at ${podIp(attempt.index)}.` : "Empty because the Service's selector matches no pod. Broken by design.",
        scope: "lane",
        tags: ["fixture"],
        facts: [{ label: "Addresses", value: addresses ? podIp(attempt.index) : "None" }],
      });
      link("contains", "ns:default", "fixture:svc", "contains", "Removed with its namespace.", true);
      link("contains", "ns:default", "fixture:ep", "contains", "Removed with its namespace.", true);
      link("routes-to", "fixture:svc", "fixture:ep", "endpoints", "The Service has no endpoints to send traffic to.", true);
      link("routes-to", "fixture:ep", "fixture:pod", "address", "The pod's address drops out of the Endpoints.", true, { broken: !addresses && !gone });
    }
  } else {
    add({
      id: "fixture:pod",
      kind: "pod",
      kindLabel: "Pod · fixture",
      name: "No fixture",
      parent: "ns:default",
      health: "stopped",
      status: "None deployed",
      reason:
        campaignStatus === "running"
          ? "Between attempts: the last fixture was torn down and the next isn't created yet."
          : campaignStatus === "completed"
            ? "Campaign complete. Teardown restored the lane's baseline."
            : "Campaign stopped. Teardown removed the failed fixture.",
      scope: "lane",
      tags: ["fixture"],
    });
  }

  for (const pod of laneProfile.pods.filter((p) => p.kind !== "fixture")) {
    const id = pod.kind === "system" ? systemId(pod.name) : `pod:${pod.name}`;
    const role = SYSTEM_ROLES[id.slice(4)];
    add({
      id,
      kind: "pod",
      kindLabel: pod.kind === "system" ? "Pod · system" : "Pod · leftover",
      name: pod.name,
      parent: `ns:${pod.namespace}`,
      health: pod.kind === "leftover" ? "leftover" : "healthy",
      status: `${pod.status} · ${pod.ready}`,
      reason: pod.kind === "leftover" ? (pod.note ?? "Known leftover.") : `Running. ${role ?? ""}`.trim(),
      scope: "lane",
      tags: pod.kind === "leftover" ? ["leftover"] : ["system"],
      facts: [
        { label: "Ready", value: pod.ready },
        { label: "Restarts", value: pod.restarts.toLocaleString() },
        { label: "Age", value: pod.age },
        ...(pod.kind === "leftover" ? [{ label: "Owner", value: "No case or campaign" }] : []),
      ],
    });
  }
  for (const pod of nodes.filter((n) => n.kind === "pod" && n.name !== "No fixture")) {
    link("contains", pod.parent!, pod.id, "contains", "Removed with its namespace.", true);
    link("runs-on", pod.id, "node:minh-lane", "scheduled on", "Pods stop when their node goes down.", true);
  }

  // Hosting relationships
  link("runs-on", "docker", "host", "runs on", "Docker stops with the host.", true);
  link("contains", "host", "gpu-0", "contains", "Unavailable with the host.", true);
  link("contains", "host", "gpu-1", "contains", "Unavailable with the host.", true);
  link("runs-on", "pgvector", "docker", "runs on", "The pgvector container stops with Docker.", true);
  for (const id of ["rag", "ollama", "operator", "worker"]) link("runs-on", id, "host", "runs on", "The process stops with the host.", true);
  link("runs-on", "ollama", "gpu-0", "GPU 0", "Ollama can't serve the local model from GPU 0.", true);

  // Calls and serving
  link("depends-on", "operator", "worker", "reads job state", "The operator app loses the job's events and marks the job interrupted.", false);
  link("serves", "rag", "worker", "retrieval", "The knowledge agent can't retrieve passages, so attempts error.", false);
  link("serves", "openai", "worker", apiModelFor(key, attempt?.model), "API-model roles (knowledge, verifier, gpt-6-luna) can't reach their models, so attempts error.", false);
  link("serves", "ollama", "worker", "glm-4.7-flash", "glm-4.7-flash attempts can't run; API-model attempts are unaffected.", false);
  link("depends-on", "worker", "sys:kube-apiserver", "kubectl", "kubectl to minh-lane fails, so setup, debug, Ground Truth checks, and teardown can't run.", false);
  if (fixture && attempt) {
    link("depends-on", "worker", "fixture:pod", "probes", "The verifier and Ground Truth see a broken app. That's recorded as the attempt's outcome, not a lab fault.", false, { outcome: true });
  }
  link("depends-on", "rag", "pgvector", "queries", "Retrieval queries fail, so the RAG API returns errors.", true);
  link("depends-on", "sys:kube-apiserver", "sys:etcd", "stores state", "The API server loses its datastore and stops answering.", true);
  link("depends-on", "sys:kube-controller-manager", "sys:kube-apiserver", "watches", "Reconciliation stops while the API server is down.", false);
  link("depends-on", "sys:kube-scheduler", "sys:kube-apiserver", "watches", "Pod scheduling stops while the API server is down.", false);

  // Traffic for the current phase
  const kubectlPath = ["worker", "sys:kube-apiserver", "sys:etcd"];
  const traffic: TopologyGraph["traffic"] = !phase
    ? { label: campaignStatus === "running" ? "Between attempts" : campaignStatus === "completed" ? "Campaign complete" : "Campaign stopped", paths: [] }
    : key === "setup"
      ? { label: "Setup", paths: [kubectlPath] }
      : key === "knowledge"
        ? { label: "Knowledge", paths: [["worker", "rag", "pgvector"], ["worker", "openai"]] }
        : key === "debug"
          ? { label: `Debug · ${attempt!.model.replace(/:latest$/, "")}`, paths: local ? [["worker", "ollama", "gpu-0"], kubectlPath] : [["worker", "openai"], kubectlPath] }
          : key === "verify"
            ? { label: "Verify", paths: [["worker", "openai"], ["worker", "fixture:pod"]] }
            : key === "truth"
              ? { label: "Ground Truth", paths: nodes.some((n) => n.id === "fixture:svc") ? [kubectlPath, ["fixture:svc", "fixture:ep", "fixture:pod"]] : [kubectlPath] }
              : { label: "Teardown", paths: [kubectlPath] };
  if (campaignStatus === "running") traffic.paths.push(["operator", "worker"]);
  if (failing && key === "setup") traffic.paths.splice(0, traffic.paths.length, ["operator", "worker"], kubectlPath);

  const hops = new Set<string>();
  const activeNodes = new Set<string>();
  for (const path of traffic.paths) {
    // The operator app's event stream is constant while a campaign runs; it
    // lights its edge but doesn't count as phase traffic for the nodes.
    const stream = path.length === 2 && path[0] === "operator";
    path.forEach((id, i) => {
      if (!stream) activeNodes.add(id);
      if (i) hops.add(`${path[i - 1]}|${id}`);
    });
  }
  for (const edge of edges) edge.active = !edge.broken && (hops.has(`${edge.source}|${edge.target}`) || hops.has(`${edge.target}|${edge.source}`)) && edge.kind !== "contains";
  for (const node of nodes) node.active = activeNodes.has(node.id);

  return assemble({ t, nodes, edges, attempt, phase, campaignStatus, traffic });
}

/** Indexes the nodes and summarizes every container and the lane. */
function assemble(base: Omit<TopologyGraph, "byId" | "children" | "rollups" | "lane">): TopologyGraph {
  const { nodes } = base;
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const children = new Map<string, string[]>();
  for (const node of nodes) {
    if (!node.parent) continue;
    children.set(node.parent, [...(children.get(node.parent) ?? []), node.id]);
  }
  const rollups = new Map<string, Rollup>();
  const rollupOf = (id: string): Rollup => {
    const cached = rollups.get(id);
    if (cached) return cached;
    const own = byId.get(id)!;
    const result = summarize(own, collect(id, children, byId));
    rollups.set(id, result);
    return result;
  };
  for (const id of children.keys()) rollupOf(id);

  const laneNodes = LANE_MEMBERS.flatMap((id) => [byId.get(id)!, ...collect(id, children, byId)]);
  const lane = summarize(undefined, laneNodes);

  return { ...base, byId, children, rollups, lane };
}

/** A finished preflight, as far as the graph needs it. */
export interface Preflight {
  checks: ReadinessCheck[];
  /** When it finished, for the reasons, e.g. "Nov 1 · 19:09". */
  at: string;
}

/**
 * The graph as the latest preflight shows it. A blocked preflight is newer
 * evidence about the lane than the replay: a stopped minikube profile takes
 * its node and pods out of reach (unknown), a refused API server makes the
 * cluster unreadable, and a failed lane RAG check takes the RAG API down.
 * Other checks change nothing here; a ready preflight returns the graph as is.
 */
export function withPreflight(graph: TopologyGraph, preflight: Preflight | undefined): TopologyGraph {
  if (!preflight) return graph;
  const blocked = new Map(preflight.checks.filter((c) => c.level === "block").map((c) => [c.id, c]));
  const profileStopped = blocked.has("minikube_status");
  const clusterUnreadable = profileStopped || blocked.has("cluster_access");
  const ragDown = blocked.get("rag_lane") ?? blocked.get("rag_api");
  if (!clusterUnreadable && !ragDown) return graph;

  const source = `latest preflight, ${preflight.at}`;
  const overrides = new Map<string, Partial<TopoNode>>();
  if (clusterUnreadable) {
    overrides.set(
      "profile:minh-lane",
      profileStopped
        ? { health: "stopped", status: "Stopped", reason: `The ${source}, found minikube profile 'minh-lane' stopped (minikube_status), so nothing in the lane can run until preparation starts it again.` }
        : { health: "failing", status: "Unreachable", reason: `The ${source}, could not reach the lane's API server (cluster_access): ${blocked.get("cluster_access")!.detail}` },
    );
    for (const node of collect("profile:minh-lane", graph.children, graph.byId)) {
      overrides.set(node.id, {
        health: "unknown",
        status: "Unreadable",
        reason: `${profileStopped ? "The lane's profile is stopped" : "The lane's API server refused connections"}, so this can't be read (${source}).`,
      });
    }
  }
  if (ragDown) overrides.set("rag", { health: "failing", status: "Down · no answer", reason: `The ${source}, found the lane RAG API down: ${ragDown.detail}` });

  const nodes = graph.nodes.map((node) => (overrides.has(node.id) ? { ...node, ...overrides.get(node.id), active: false } : node));
  const edges = graph.edges.map((edge) => (edge.active && (overrides.has(edge.source) || overrides.has(edge.target)) ? { ...edge, active: false } : edge));
  const result = assemble({ t: graph.t, nodes, edges, attempt: graph.attempt, phase: graph.phase, campaignStatus: graph.campaignStatus, traffic: graph.traffic });
  // Containers the preflight made unreadable summarize as such, not as "0 healthy".
  for (const id of overrides.keys()) {
    const rollup = result.rollups.get(id);
    if (rollup && clusterUnreadable && id !== "rag") {
      result.rollups.set(id, { ...rollup, reason: `${rollup.total} inside, none readable while ${profileStopped ? "the profile is stopped" : "the API server refuses connections"}.` });
    }
  }
  const failed = [...blocked.values()].filter((c) => ["minikube_status", "cluster_access", "rag_lane", "rag_api"].includes(c.id)).map((c) => c.label);
  return {
    ...result,
    lane: {
      ...result.lane,
      health: "failing",
      attention: [...new Set([...(clusterUnreadable ? ["profile:minh-lane"] : []), ...result.lane.attention])],
      reason: `From the ${source}: ${failed.join(", ")} failed. ${result.lane.reason}`,
    },
  };
}

function collect(id: string, children: Map<string, string[]>, byId: Map<string, TopoNode>): TopoNode[] {
  const out: TopoNode[] = [];
  const walk = (current: string) => {
    for (const child of children.get(current) ?? []) {
      out.push(byId.get(child)!);
      walk(child);
    }
  };
  walk(id);
  return out;
}

function emptyCounts(): Record<Health, number> {
  return { healthy: 0, degraded: 0, failing: 0, "expected-broken": 0, leftover: 0, stopped: 0, unknown: 0 };
}

// A container summarizes what it holds. Failing or degraded contents make it
// degraded; expected-broken fixtures and known leftovers are explained and
// listed, never counted against it; stopped and unknown are informational.
function summarize(own: TopoNode | undefined, members: TopoNode[]): Rollup {
  const counts = emptyCounts();
  for (const node of members) counts[node.health] += 1;
  const attention = members.filter((n) => HEALTH[n.health].attention);
  const explained = members.filter((n) => HEALTH[n.health].explained);
  let health: Health = own?.health ?? "healthy";
  if (attention.length && HEALTH[health].rank > HEALTH.degraded.rank) health = !own && attention.some((n) => n.health === "failing") ? "failing" : "degraded";
  const fixtures = counts["expected-broken"];
  const leftovers = counts.leftover;
  const parts = [
    fixtures ? `${fixtures} fixture object${fixtures === 1 ? "" : "s"} broken by design` : "",
    leftovers ? `${leftovers} known leftover${leftovers === 1 ? "" : "s"}` : "",
  ].filter(Boolean);
  const explainedNote = parts.length ? ` ${parts.join(" and ")}: explained, not counted.` : "";
  const reason = attention.length
    ? `${attention.length} need${attention.length === 1 ? "s" : ""} attention: ${attention.map((n) => `${n.name} (${HEALTH[n.health].word.toLowerCase()})`).join(", ")}.${explainedNote}`
    : `${counts.healthy} healthy.${explainedNote}`;
  return { health, reason, counts, total: members.length, attention: attention.map((n) => n.id), explained: explained.map((n) => n.id) };
}

// ---------------------------------------------------------------------------
// Impact analysis

export interface Link {
  id: string;
  edge: TopoEdge;
}

/** Which end of an edge depends on the other. */
export function ends(edge: TopoEdge): { dependent: string; dependency: string } {
  return edge.kind === "contains" || edge.kind === "serves" ? { dependent: edge.target, dependency: edge.source } : { dependent: edge.source, dependency: edge.target };
}

/** What a node directly depends on. */
export function upstream(graph: TopologyGraph, id: string): Link[] {
  return graph.edges.filter((e) => ends(e).dependent === id).map((edge) => ({ id: ends(edge).dependency, edge }));
}

/** What directly depends on a node. */
export function downstream(graph: TopologyGraph, id: string): Link[] {
  return graph.edges.filter((e) => ends(e).dependency === id).map((edge) => ({ id: ends(edge).dependent, edge }));
}

function walk(graph: TopologyGraph, id: string, step: (graph: TopologyGraph, id: string) => Link[], maxDepth = Infinity): Map<string, number> {
  const depth = new Map<string, number>([[id, 0]]);
  const queue = [id];
  while (queue.length) {
    const current = queue.shift()!;
    const d = depth.get(current)!;
    if (d >= maxDepth) continue;
    for (const next of step(graph, current)) {
      if (depth.has(next.id)) continue;
      depth.set(next.id, d + 1);
      queue.push(next.id);
    }
  }
  depth.delete(id);
  return depth;
}

/** Everything a node needs, transitively, with hop distance. */
export const upstreamAll = (graph: TopologyGraph, id: string, maxDepth?: number) => walk(graph, id, upstream, maxDepth);
/** Everything that needs a node, transitively, with hop distance. */
export const downstreamAll = (graph: TopologyGraph, id: string, maxDepth?: number) => walk(graph, id, downstream, maxDepth);

/** A node plus its dependencies and dependents within a number of hops. */
export function neighborhood(graph: TopologyGraph, id: string, hops = 1): Set<string> {
  return new Set([id, ...upstreamAll(graph, id, hops).keys(), ...downstreamAll(graph, id, hops).keys()]);
}

export type Effect = "down" | "impaired" | "outcome";
export const EFFECT: Record<Effect, { word: string; rank: number }> = {
  down: { word: "Goes down", rank: 0 },
  impaired: { word: "Impaired", rank: 1 },
  outcome: { word: "Attempt outcome", rank: 2 },
};

export interface Impact {
  id: string;
  effect: Effect;
  depth: number;
  via: string;
  edge: TopoEdge;
  reason: string;
}

export interface WhatIf {
  root: string;
  impacts: Impact[];
  byId: Map<string, Impact>;
  /** Readiness checks that would block new campaigns. */
  blocked: ReadinessCheck[];
  notes: string[];
}

// Simulates the node failing. "Down" travels through hard dependencies (runs
// on, contains, a datastore); a soft dependency only impairs its dependent, and
// impairment doesn't travel further. Already stopped nodes have nothing to lose.
export function whatIf(graph: TopologyGraph, root: string): WhatIf {
  const byId = new Map<string, Impact>();
  const queue: { id: string; effect: Exclude<Effect, "outcome">; depth: number }[] = [{ id: root, effect: "down", depth: 0 }];
  while (queue.length) {
    const current = queue.shift()!;
    for (const next of downstream(graph, current.id)) {
      if (next.id === root) continue;
      const node = graph.byId.get(next.id);
      if (!node || node.health === "stopped") continue;
      if (current.effect === "impaired" && !next.edge.hard) continue;
      const effect: Effect = next.edge.outcome ? "outcome" : current.effect === "down" && next.edge.hard ? "down" : "impaired";
      const existing = byId.get(next.id);
      if (existing && EFFECT[existing.effect].rank <= EFFECT[effect].rank) continue;
      byId.set(next.id, { id: next.id, effect, depth: current.depth + 1, via: current.id, edge: next.edge, reason: next.edge.impact });
      if (effect !== "outcome") queue.push({ id: next.id, effect, depth: current.depth + 1 });
    }
  }
  const impacts = [...byId.values()].sort((a, b) => a.depth - b.depth || EFFECT[a.effect].rank - EFFECT[b.effect].rank);
  const hit = new Set([root, ...impacts.filter((i) => i.effect !== "outcome").map((i) => i.id)]);
  const checkIds = new Set([...hit].flatMap((id) => CHECKS_BY_NODE[id] ?? []));
  const blocked = READY_CHECKS.filter((c) => checkIds.has(c.id));

  const node = graph.byId.get(root);
  const notes: string[] = [];
  if (root === "openai") notes.push("Preflight confirms OpenAI credentials exist, not that the API is up; an outage would surface as attempt errors.");
  if (root === "operator") notes.push("The worker is a detached process, so the campaign keeps running without the app.");
  if (root === "sys:kube-apiserver" || root === "sys:etcd") notes.push("Running pods keep running without the API server; only changes stop.");
  if (node?.tags.includes("fixture")) notes.push("This is the case under test. Its failure is what the agents are asked to repair.");
  if (node?.tags.includes("leftover")) notes.push("A known leftover: nothing in the lab depends on it.");
  if (node?.health === "stopped") notes.push("Already stopped: nothing running depends on it.");
  if (root === "gpu-1") notes.push("Another account's GPU: nothing in KubeLLM uses it.");
  if (byId.has("worker") && byId.get("worker")!.effect !== "outcome" && graph.campaignStatus === "running") {
    notes.push("Attempts that need it would error. Runner errors are reported apart from Ground Truth outcomes and don't count against a model.");
  }
  if (!impacts.length && !notes.length) notes.push(`Nothing depends on ${node?.name ?? root}.`);
  return { root, impacts, byId, blocked, notes };
}

// ---------------------------------------------------------------------------
// Change history over the replay

export interface NodeState {
  health: Health;
  status: string;
  name: string;
  active: boolean;
  /** Containers: the summarized health of what they hold. */
  rollup?: Health;
}

export interface Snapshot {
  t: number;
  states: Map<string, NodeState>;
  phase?: string;
  attempt?: number;
}

const SNAPSHOTS = new WeakMap<DemoCampaign, Snapshot[]>();

const stateOf = (graph: TopologyGraph) =>
  new Map<string, NodeState>(graph.nodes.map((n) => [n.id, { health: n.health, status: n.status, name: n.name, active: n.active, rollup: graph.rollups.get(n.id)?.health }]));

/** The graph sampled at every moment something can change: phase edges, model keep-alive, the other account's GPU job. */
export function snapshots(campaign: DemoCampaign): Snapshot[] {
  const cached = SNAPSHOTS.get(campaign);
  if (cached) return cached;
  const times = new Set<number>([0]);
  for (const attempt of campaign.attempts) {
    for (const phase of attempt.phases) times.add(phase.start + 0.01);
    times.add(attempt.end + 0.01);
    if (isLocalModel(attempt.model)) times.add(attempt.end + 300.01);
  }
  for (let k = 0; k * 900 < campaign.total; k++) {
    times.add(k * 900 + 420.01);
    times.add(k * 900 + 720.01);
  }
  const list = [...times]
    .filter((t) => t <= campaign.total)
    .sort((a, b) => a - b)
    .map((t) => {
      const graph = graphAt(campaign, t);
      return { t, states: stateOf(graph), phase: graph.phase?.label, attempt: graph.attempt?.index };
    });
  SNAPSHOTS.set(campaign, list);
  return list;
}

export interface Change {
  t: number;
  from?: NodeState;
  to: NodeState;
  attempt?: number;
  phase?: string;
}

/** Status and health changes for one node up to time t, newest first. */
export function changesFor(campaign: DemoCampaign, id: string, t: number, limit = 6): Change[] {
  const out: Change[] = [];
  let previous: NodeState | undefined;
  for (const snap of snapshots(campaign)) {
    if (snap.t > t) break;
    const state = snap.states.get(id);
    if (!state) continue;
    if (!previous || previous.health !== state.health || previous.status !== state.status || previous.name !== state.name) {
      out.push({ t: snap.t, from: previous, to: state, attempt: snap.attempt, phase: snap.phase });
    }
    previous = state;
  }
  return out.reverse().slice(0, limit);
}

export interface PhaseColumn {
  attempt: DemoAttempt;
  phase: DemoPhase;
  states: Map<string, NodeState>;
}

const COLUMNS = new WeakMap<DemoCampaign, PhaseColumn[]>();

/** Every phase of every attempt, sampled at its midpoint: what each component looked like then. */
export function phaseColumns(campaign: DemoCampaign): PhaseColumn[] {
  const cached = COLUMNS.get(campaign);
  if (cached) return cached;
  const columns = campaign.attempts.flatMap((attempt) =>
    attempt.phases.map((phase) => ({ attempt, phase, states: stateOf(graphAt(campaign, (phase.start + phase.end) / 2)) })),
  );
  COLUMNS.set(campaign, columns);
  return columns;
}
