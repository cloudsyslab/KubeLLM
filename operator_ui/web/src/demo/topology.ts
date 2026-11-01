import { caseFamily } from "@/lib/cases";
import { FAILURE_ATTEMPT, type DemoCampaign } from "./campaign";

// Simulated cluster inventory shaped like the lab survey: five minikube
// profiles, only minh-lane running and selected, the default kubectl context
// pointing at a stopped profile, and two long-failing leftover pods in the lane.

export type PodStatus = "Running" | "CrashLoopBackOff" | "ImagePullBackOff" | "ErrImagePull" | "ContainerCreating" | "Terminating";

export interface Pod {
  name: string;
  namespace: string;
  status: PodStatus;
  ready: string;
  restarts: number;
  age: string;
  kind: "system" | "fixture" | "leftover";
  note?: string;
}

export interface Profile {
  name: string;
  status: "Running" | "Stopped" | "Unknown";
  selected: boolean;
  defaultContext: boolean;
  kubernetes: string;
  driver: string;
  nodes: { name: string; status: "Ready" | "NotReady" | "Unknown"; ip?: string }[];
  pods: Pod[];
}

export interface LaneService {
  name: string;
  detail: string;
  status: "Healthy" | "Unknown";
  uptime: string;
}

const SYSTEM_PODS = ["coredns-6f6b679f8f-q2x7d", "etcd-minh-lane", "kube-apiserver-minh-lane", "kube-controller-manager-minh-lane", "kube-proxy-8kq4n", "kube-scheduler-minh-lane", "storage-provisioner"];

const LEFTOVERS: Pod[] = [
  { name: "curl-pod", namespace: "default", status: "CrashLoopBackOff", ready: "0/1", restarts: 9457, age: "33d", kind: "leftover", note: "Not created by this campaign and not owned by any case's teardown. Failing for 33 days; review before removing." },
  { name: "tmpcurl", namespace: "default", status: "ImagePullBackOff", ready: "0/1", restarts: 0, age: "33d", kind: "leftover", note: "Not created by this campaign and not owned by any case's teardown. Its image never pulled." },
];

function brokenState(caseId: string): { status: PodStatus; ready: string; restarts: number; note: string } {
  const { family } = caseFamily(caseId);
  if (["environment_variable", "missing_dependency", "resource_limits"].includes(family) && caseId !== "resource_limits_cpu_starvation") {
    return { status: "CrashLoopBackOff", ready: "0/1", restarts: 4, note: "Expected: the fixture crashes until the agent repairs it." };
  }
  if (family === "liveness_probe") return { status: "Running", ready: "1/1", restarts: 6, note: "Expected: the liveness probe keeps restarting the container." };
  if (family.startsWith("readiness") || caseId === "resource_limits_cpu_starvation") return { status: "Running", ready: "0/1", restarts: 0, note: "Expected: the pod never becomes Ready." };
  return { status: "Running", ready: "1/1", restarts: 0, note: "Expected: the pod runs but the application is unreachable." };
}

export function topologyAt(campaign: DemoCampaign, t: number): { profiles: Profile[]; services: LaneService[] } {
  const attempt = campaign.attempts.find((a) => t >= a.start && t < a.end);
  const phase = attempt?.phases.find((p) => t >= p.start && t < p.end);
  const fixtures: Pod[] = [];
  if (attempt && phase) {
    const name = attempt.caseId.replaceAll("_", "-").slice(0, 28);
    const age = `${Math.max(1, Math.round(t - attempt.start))}s`;
    const failing = campaign.failure && attempt.index === FAILURE_ATTEMPT;
    if (failing) {
      fixtures.push({ name, namespace: "default", status: "ErrImagePull", ready: "0/1", restarts: 0, age, kind: "fixture", note: "Setup error: the fixture image is missing. This stops the campaign; teardown removes the pod." });
    } else if (phase.key === "setup") {
      fixtures.push({ name, namespace: "default", status: "ContainerCreating", ready: "0/1", restarts: 0, age, kind: "fixture", note: "Benchmark fixture being created." });
    } else if (phase.key === "teardown") {
      fixtures.push({ name, namespace: "default", status: "Terminating", ready: "0/1", restarts: 0, age, kind: "fixture", note: "Scoped teardown is removing this case's resources." });
    } else {
      const repaired = attempt.outcome === "pass" && ["verify", "truth"].includes(phase.key);
      const broken = brokenState(attempt.caseId);
      fixtures.push(
        repaired
          ? { name, namespace: "default", status: "Running", ready: "1/1", restarts: broken.restarts, age, kind: "fixture", note: "Repaired by the debug agent; Ground Truth decides the outcome." }
          : { name, namespace: "default", age, kind: "fixture", ...broken },
      );
    }
  }

  return {
    profiles: [
      {
        name: "minh-lane",
        status: "Running",
        selected: true,
        defaultContext: false,
        kubernetes: "v1.31.0",
        driver: "docker",
        nodes: [{ name: "minh-lane", status: "Ready", ip: "192.168.112.2" }],
        pods: [
          ...fixtures,
          ...LEFTOVERS,
          ...SYSTEM_PODS.map((name) => ({ name, namespace: "kube-system", status: "Running" as const, ready: "1/1", restarts: 0, age: "38d", kind: "system" as const })),
        ],
      },
      { name: "minikube", status: "Stopped", selected: false, defaultContext: true, kubernetes: "v1.31.0", driver: "docker", nodes: [{ name: "minikube", status: "Unknown" }], pods: [] },
      { name: "minh", status: "Unknown", selected: false, defaultContext: false, kubernetes: "v1.31.0", driver: "docker", nodes: [{ name: "minh", status: "Unknown" }], pods: [] },
      { name: "lamap", status: "Unknown", selected: false, defaultContext: false, kubernetes: "v1.31.0", driver: "docker", nodes: [{ name: "lamap", status: "Unknown" }], pods: [] },
      { name: "xyz", status: "Unknown", selected: false, defaultContext: false, kubernetes: "v1.31.0", driver: "docker", nodes: [{ name: "xyz", status: "Unknown" }], pods: [] },
    ],
    services: [
      { name: "RAG API", detail: "127.0.0.1:18004 · lane minh", status: "Healthy", uptime: "34d" },
      { name: "pgvector", detail: "kubellm-minh-lane-pgvector", status: "Healthy", uptime: "5w" },
      { name: "Ollama", detail: "127.0.0.1:11434 · 9 models", status: "Healthy", uptime: "—" },
    ],
  };
}
