import type {
  DataSourceInfo,
  JobEvent,
  OverviewSnapshot,
  OperatorCase,
  OperatorJob,
  PublishPreview,
  RunWithCases,
  RunsSnapshot,
  TelemetrySample,
  TopologySnapshot,
} from "./types";

// One interface, two sources. Fixture mode reads the committed snapshot of real
// recorded exports; api mode calls the FastAPI backend. Select with
// VITE_OPERATOR_DATA=api at build time (default: fixture).
export interface OperatorApi {
  source: DataSourceInfo;
  isLive: boolean;
  explorerRuns(): Promise<RunWithCases[]>;
  overview(): Promise<OverviewSnapshot>;
  cases(): Promise<OperatorCase[]>;
  jobs(): Promise<OperatorJob[]>;
  job(id: string): Promise<OperatorJob>;
  runReadiness(): Promise<OperatorJob>;
  prepare(): Promise<OperatorJob>;
  startCampaign(input: CampaignInput): Promise<OperatorJob>;
  stopJob(id: string): Promise<OperatorJob>;
  telemetry(): Promise<TelemetrySample>;
  topology(): Promise<TopologySnapshot>;
  publishPreview(id: string): Promise<PublishPreview>;
  publishPreviewFile(id: string, path: string): Promise<{ path: string; content: string }>;
  publish(id: string, token: string): Promise<OperatorJob>;
}

export interface CampaignInput {
  cases: string[];
  techniques: string[];
  debug_models: string[];
  api_model: string;
  verification_model: string;
  repetitions: number;
}

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function sendJson<T>(path: string, method: "POST", body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(typeof payload.detail === "string" ? payload.detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function unavailable<T>(): Promise<T> {
  throw new Error("This action is available when the operator is connected to its backend.");
}

let snapshot: Promise<RunsSnapshot> | null = null;
function loadSnapshot(): Promise<RunsSnapshot> {
  snapshot ??= import("@/data/runs.snapshot.json").then((module) => module.default as unknown as RunsSnapshot);
  return snapshot;
}

const fixtureApi: OperatorApi = {
  source: { mode: "fixture", label: "Recorded snapshot" },
  isLive: false,
  async explorerRuns() {
    return (await loadSnapshot()).runs;
  },
  overview: unavailable,
  cases: unavailable,
  jobs: unavailable,
  job: unavailable,
  runReadiness: unavailable,
  prepare: unavailable,
  startCampaign: unavailable,
  stopJob: unavailable,
  telemetry: unavailable,
  topology: unavailable,
  publishPreview: unavailable,
  publishPreviewFile: unavailable,
  publish: unavailable,
};

// GET /api/explorer is part of the contract in operator_ui/web/API_CONTRACT.md:
// every recorded run as public_run plus its case rows.
const httpApi: OperatorApi = {
  source: { mode: "api", label: "Live backend" },
  isLive: true,
  async explorerRuns() {
    return (await readJson<{ runs: RunWithCases[] }>("/api/explorer")).runs;
  },
  async overview() {
    return readJson("/api/overview");
  },
  async cases() {
    return (await readJson<{ cases: OperatorCase[] }>("/api/cases")).cases;
  },
  async jobs() {
    return (await readJson<{ jobs: OperatorJob[] }>("/api/jobs")).jobs;
  },
  async job(id) {
    return readJson(`/api/jobs/${encodeURIComponent(id)}`);
  },
  runReadiness() {
    return sendJson("/api/readiness", "POST");
  },
  prepare() {
    return sendJson("/api/prepare", "POST");
  },
  startCampaign(input) {
    return sendJson("/api/campaign", "POST", input);
  },
  stopJob(id) {
    return sendJson(`/api/jobs/${encodeURIComponent(id)}/stop`, "POST");
  },
  telemetry() {
    return readJson("/api/telemetry");
  },
  topology() {
    return readJson("/api/topology");
  },
  publishPreview(id) {
    return sendJson(`/api/publish/preview/${encodeURIComponent(id)}`, "POST");
  },
  publishPreviewFile(id, path) {
    const query = new URLSearchParams({ path });
    return readJson(`/api/publish/preview/${encodeURIComponent(id)}/file?${query.toString()}`);
  },
  publish(id, token) {
    return sendJson("/api/publish", "POST", { job_id: id, preview_token: token });
  },
};

export function openJobEvents(id: string, onEvent: (event: JobEvent) => void, onOpen?: () => void, onError?: () => void, stopAfterClose = false, onClose?: () => void): () => void {
  const source = new EventSource(`/api/jobs/${encodeURIComponent(id)}/events`, { withCredentials: true });
  let opened = false;
  let closed = false;
  source.onopen = () => { opened = true; onOpen?.(); };
  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as JobEvent);
    } catch {
      onError?.();
    }
  };
  source.onerror = () => {
    onError?.();
    if (stopAfterClose && opened && !closed) {
      closed = true;
      source.close();
      onClose?.();
    }
  };
  return () => { closed = true; source.close(); };
}

export const api: OperatorApi = import.meta.env.VITE_OPERATOR_DATA === "api" ? httpApi : fixtureApi;

export async function snapshotGeneratedAt(): Promise<string | undefined> {
  if (api.source.mode !== "fixture") return undefined;
  return (await loadSnapshot()).generated_at;
}
