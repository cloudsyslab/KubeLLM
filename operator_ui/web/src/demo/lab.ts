import { noise, type DemoCampaign, type DemoAttempt, type DemoPhase } from "./campaign";

// Simulated host telemetry shaped like the lab server surveyed on 2026-11-01:
// 128 threads, 755 GiB RAM, a 438 GB root disk at ~98%, two A40s with 46 GB.
// Sources the real backend will use: PCP pmproxy (host) and nvidia-smi (GPU).

export const HOST = {
  name: "lab server",
  threads: 128,
  memTotalGiB: 755,
  diskTotalGB: 438,
  diskUsedGB: 408,
  diskFreeGB: 12,
  gpus: [
    { index: 0, name: "NVIDIA A40", vramGB: 46 },
    { index: 1, name: "NVIDIA A40", vramGB: 46 },
  ],
};

const OLLAMA_KEEPALIVE_S = 300;
const OLLAMA_VRAM_GB = 19.4;

export interface HostSample {
  t: number;
  cpu: number;
  load1: number;
  memUsedGiB: number;
  memCacheGiB: number;
  rxMBs: number;
  txMBs: number;
  gpus: { util: number; vramGB: number; tempC: number; powerW: number }[];
}

export interface ProcessRow {
  pid: number;
  user: "minh" | "root" | "other user";
  name: string;
  role: string;
  cpu: number;
  memGiB: number;
  gpu?: { index: number; memGB: number };
  attribution: "lane" | "shared" | "other";
}

function activeAt(campaign: DemoCampaign, t: number): { attempt?: DemoAttempt; phase?: DemoPhase } {
  const attempt = campaign.attempts.find((a) => t >= a.start && t < a.end);
  return { attempt, phase: attempt?.phases.find((p) => t >= p.start && t < p.end) };
}

const isLocal = (model?: string) => !!model && model.includes(":");

function ollamaLoaded(campaign: DemoCampaign, t: number): boolean {
  return campaign.attempts.some((a) => isLocal(a.model) && t >= a.start && t < a.end + OLLAMA_KEEPALIVE_S && a.phases.some((p) => p.key === "debug" && t >= p.start));
}

// Another researcher's job on GPU 1, on its own schedule. It overlaps the
// campaign by coincidence, which the UI must not attribute to the run.
function otherJob(t: number): number {
  const cycle = t % 900;
  return cycle > 420 && cycle < 720 ? 0.22 + noise(Math.floor(t / 3) + 5) * 0.14 : 0;
}

export function sampleAt(campaign: DemoCampaign, t: number): HostSample {
  const { attempt, phase } = activeAt(campaign, t);
  const step = Math.floor(t / 2);
  const localDebug = phase?.key === "debug" && isLocal(attempt?.model);
  const busyCluster = phase?.key === "setup" || phase?.key === "teardown";
  const apiCall = phase && ["knowledge", "verify"].includes(phase.key) || (phase?.key === "debug" && !isLocal(attempt?.model));
  const loaded = ollamaLoaded(campaign, t);
  const other = otherJob(t);

  const gpu0 = localDebug ? 0.68 + noise(step) * 0.28 : loaded ? 0.01 + noise(step) * 0.02 : 0;
  const cpu = 0.025 + noise(step + 11) * 0.015 + (busyCluster ? 0.05 : 0) + (localDebug ? 0.07 : 0);
  return {
    t,
    cpu,
    load1: 0.3 + cpu * 40 + noise(step + 3) * 0.4,
    memUsedGiB: 10.4 + (loaded ? 2.1 : 0) + (busyCluster ? 0.6 : 0) + noise(step + 7) * 0.3,
    memCacheGiB: 256 + noise(Math.floor(t / 60)) * 2,
    rxMBs: (busyCluster ? 2.4 + noise(step + 13) * 4 : 0.02) + (apiCall ? 0.18 + noise(step + 17) * 0.2 : 0),
    txMBs: (apiCall ? 0.06 + noise(step + 19) * 0.08 : 0.01) + (busyCluster ? 0.2 : 0),
    gpus: [
      { util: gpu0, vramGB: loaded ? OLLAMA_VRAM_GB + noise(step + 23) * 0.3 : 0.5, tempC: 23 + gpu0 * 38, powerW: 22 + gpu0 * 228 },
      { util: other, vramGB: other ? 6.1 : 0.4, tempC: 22 + other * 34, powerW: 21 + other * 200 },
    ],
  };
}

export function historyAt(campaign: DemoCampaign, t: number, points = 90, every = 2): HostSample[] {
  return Array.from({ length: points }, (_, i) => sampleAt(campaign, Math.max(0, t - (points - 1 - i) * every)));
}

export function threadLoadsAt(campaign: DemoCampaign, t: number): number[] {
  const { attempt, phase } = activeAt(campaign, t);
  const step = Math.floor(t / 2);
  const localDebug = phase?.key === "debug" && isLocal(attempt?.model);
  const busyCluster = phase?.key === "setup" || phase?.key === "teardown";
  return Array.from({ length: HOST.threads }, (_, thread) => {
    let load = noise(thread * 7 + step) * 0.06;
    if (busyCluster && thread % 16 < 4) load += 0.2 + noise(thread + step * 3) * 0.45;
    if (localDebug && thread >= 32 && thread < 48) load += 0.35 + noise(thread * 3 + step) * 0.5;
    if (otherJob(t) && thread >= 96 && thread < 100) load += 0.6 + noise(thread + step) * 0.3;
    return Math.min(1, load);
  });
}

export function processesAt(campaign: DemoCampaign, t: number): ProcessRow[] {
  const sample = sampleAt(campaign, t);
  const { attempt, phase } = activeAt(campaign, t);
  const step = Math.floor(t / 2);
  const loaded = ollamaLoaded(campaign, t);
  const rows: ProcessRow[] = [
    {
      pid: 2214907,
      user: "minh",
      name: "python3",
      role: attempt ? `KubeLLM runner · attempt ${attempt.index + 1} · ${phase?.label ?? "between phases"}` : "KubeLLM runner · idle",
      cpu: attempt ? 0.04 + noise(step + 31) * 0.06 : 0.001,
      memGiB: 0.42,
      attribution: "lane",
    },
    { pid: 1189, user: "root", name: "dockerd", role: "Docker daemon (minikube lanes)", cpu: 0.02 + (phase?.key === "setup" ? 0.3 : 0) * noise(step + 37), memGiB: 0.9, attribution: "shared" },
    { pid: 3311, user: "root", name: "kubelet", role: "minh-lane node agent", cpu: 0.03 + noise(step + 41) * 0.05, memGiB: 0.31, attribution: "lane" },
    { pid: 4086235, user: "minh", name: "uvicorn", role: "KubeLLM operator app", cpu: 0.004 + noise(step + 43) * 0.01, memGiB: 0.12, attribution: "lane" },
    { pid: 1493494, user: "minh", name: "python3", role: "RAG API · lane minh", cpu: phase?.key === "knowledge" ? 0.08 + noise(step) * 0.1 : 0.002, memGiB: 1.7, attribution: "lane" },
    { pid: 21877, user: "root", name: "postgres", role: "pgvector · lane minh", cpu: phase?.key === "knowledge" ? 0.03 : 0.001, memGiB: 0.64, attribution: "lane" },
    { pid: 1802, user: "root", name: "pmcd", role: "Performance Co-Pilot", cpu: 0.002, memGiB: 0.05, attribution: "shared" },
  ];
  if (loaded) {
    rows.push({
      pid: 3920114,
      user: "root",
      name: "ollama",
      role: "Ollama runner · glm-4.7-flash:latest",
      cpu: sample.gpus[0].util > 0.2 ? 0.08 + noise(step + 47) * 0.1 : 0.003,
      memGiB: 2.1,
      gpu: { index: 0, memGB: sample.gpus[0].vramGB - 0.5 },
      attribution: "shared",
    });
  }
  if (sample.gpus[1].util > 0) {
    rows.push({ pid: 3998001, user: "other user", name: "python3", role: "Another account's process", cpu: 0.03 + noise(step + 53) * 0.03, memGiB: 3.4, gpu: { index: 1, memGB: 5.7 }, attribution: "other" });
  }
  return rows.sort((a, b) => b.cpu - a.cpu);
}
