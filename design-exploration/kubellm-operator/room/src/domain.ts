export type DirectionId = "atlas" | "signal" | "fieldnotes";
export type PageId = "explorer" | "execution" | "lab";
export type MetricId = "success" | "cost" | "speed";
export type Tone = "good" | "warn" | "bad" | "muted" | "live";

export interface ModelScore {
  id: string;
  label: string;
  family: string;
  success: number;
  cost: number;
  speed: number;
  coverage: number;
  attempts: number;
  runs: number;
  shift: number;
  color: string;
}

export interface EvalCase {
  id: string;
  label: string;
  area: string;
  scores: Array<number | null>;
}

export interface EventRow {
  time: string;
  level: "INFO" | "OK" | "WARN" | "ERROR";
  message: string;
  detail: string;
  stage: string;
}

export interface LabProfile {
  id: string;
  label: string;
  status: "running" | "stopped" | "unknown";
  context: string;
  nodes: number;
  workloads: number;
  pods: number;
  affected: boolean;
}

export interface ResourcePoint {
  time: string;
  cpu: number;
  memory: number;
  gpu0: number;
  gpu1: number;
  vram0: number;
  vram1: number;
}

export interface DirectionProps {
  page: PageId;
  onPageChange: (page: PageId) => void;
  metric: MetricId;
  onMetricChange: (metric: MetricId) => void;
  selectedModelId: string;
  onModelSelect: (id: string) => void;
  selectedCaseId: string;
  onCaseSelect: (id: string) => void;
  live: boolean;
  onLiveChange: (live: boolean) => void;
}
