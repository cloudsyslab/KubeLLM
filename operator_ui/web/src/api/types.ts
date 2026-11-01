// Shapes mirror operator_ui/results.py (public_run and case rows) so the fixture
// snapshot and the live backend are interchangeable.

export type Technique = "allStepsAtOnce" | "stepByStep" | "singleAgent" | "knowledgeAgentOnly";
export type RunSource = "canonical" | "exploratory" | "local";
export type CaseStatus = "PASS" | "FAIL" | "ERROR" | "TIMEOUT" | "UNKNOWN";

export interface RoleMetrics {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  cost?: number;
  duration_s?: number;
}

export interface CaseRow {
  case: string;
  status: CaseStatus;
  ground_truth_passed: boolean | null;
  ground_truth_configured: boolean | null;
  verified: boolean | null;
  technique: Technique | null;
  duration_s: number | null;
  metrics: Partial<Record<"api" | "debug" | "verification", RoleMetrics>>;
}

export interface Run {
  ref: string;
  run_id: string;
  source: RunSource;
  source_group: string;
  archived: boolean;
  technique: Technique | null;
  models: { API: string[]; DebugAgent: string[]; Verification: string[] };
  cases: string[];
  planned_cases: number;
  observed_cases: number;
  ground_truth_known: number;
  ground_truth_passed: number;
  ground_truth_rate: number | null;
  ground_truth_unavailable: number;
  ground_truth_missing: number;
  ground_truth_not_configured: number;
  verification_known: number;
  verification_correct: number;
  verification_comparable: number;
  total_cost: number | null;
  total_tokens: number | null;
  duration_s: number | null;
  pass_rate: number | null;
  status: "recorded" | "incomplete";
}

export interface RunWithCases extends Run {
  case_rows: CaseRow[];
}

export interface RunsSnapshot {
  generated_at: string;
  producer: string;
  runs: RunWithCases[];
}

export interface DataSourceInfo {
  mode: "fixture" | "api";
  label: string;
  generatedAt?: string;
}
