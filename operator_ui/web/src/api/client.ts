import type { DataSourceInfo, RunWithCases, RunsSnapshot } from "./types";

// One interface, two sources. Fixture mode reads the committed snapshot of real
// recorded exports; api mode calls the FastAPI backend. Select with
// VITE_OPERATOR_DATA=api at build time (default: fixture).
export interface OperatorApi {
  source: DataSourceInfo;
  explorerRuns(): Promise<RunWithCases[]>;
}

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

let snapshot: Promise<RunsSnapshot> | null = null;
function loadSnapshot(): Promise<RunsSnapshot> {
  snapshot ??= import("@/data/runs.snapshot.json").then((module) => module.default as unknown as RunsSnapshot);
  return snapshot;
}

const fixtureApi: OperatorApi = {
  source: { mode: "fixture", label: "Recorded snapshot" },
  async explorerRuns() {
    return (await loadSnapshot()).runs;
  },
};

// GET /api/explorer is part of the contract in operator_ui/web/API_CONTRACT.md:
// every recorded run as public_run plus its case rows.
const httpApi: OperatorApi = {
  source: { mode: "api", label: "Live backend" },
  async explorerRuns() {
    return (await readJson<{ runs: RunWithCases[] }>("/api/explorer")).runs;
  },
};

export const api: OperatorApi = import.meta.env.VITE_OPERATOR_DATA === "api" ? httpApi : fixtureApi;

export async function snapshotGeneratedAt(): Promise<string | undefined> {
  if (api.source.mode !== "fixture") return undefined;
  return (await loadSnapshot()).generated_at;
}
