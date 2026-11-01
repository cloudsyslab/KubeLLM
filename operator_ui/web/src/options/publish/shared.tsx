import clsx from "clsx";
import { ChevronRight, File, FileBraces, FileText, Folder, FolderOpen } from "lucide-react";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import data from "@/data/cases.json";
import { jobById, PUBLISH_PREVIEW } from "@/demo/jobs";
import { count } from "@/lib/format";
import { CheckMark, countdown, stamp } from "../environment/readiness";

// The publication preview and job, mirrored from operator_ui/publishing.py.
// Preview first (sanitized copy, hashes, token, 30-minute expiry); publishing
// re-verifies everything, copies the reviewed files, stages only those paths,
// commits them, and pushes. Demo values come from PUBLISH_PREVIEW.

export const P = PUBLISH_PREVIEW;
export const CAMPAIGN = jobById(P.campaignJobId);
export const PREVIEW_TTL_MIN = 30;
/**
 * publishing.py pushes after committing ("Pushing the export commit to the
 * configured upstream."). Flip this if the backend drops the push.
 */
export const PUSHES_AFTER_COMMIT = true;

export const SHORT_ID = P.campaignJobId.slice(0, 8);
export const COMMIT_MESSAGE = `Archive KubeLLM operator campaign ${SHORT_ID}`;
export const MODELS = [...new Set(Object.values(P.models))].sort();
const CASES = Object.keys((data as unknown as { cases: Record<string, unknown> }).cases).sort();
const REPS = CAMPAIGN?.campaign?.repetitions ?? 5;
const TECHNIQUE = P.techniques[0];

export const ATTEMPTS = Array.from({ length: P.attempts.recorded }, (_, i) => {
  const caseId = CASES[Math.floor(i / REPS) % CASES.length];
  const seq = i + 1;
  return { seq, caseId, rep: (i % REPS) + 1, dir: `${TECHNIQUE}/attempt-${String(seq).padStart(4, "0")}-${caseId}` };
});

export const PACK_FILE_COUNT = P.attempts.recorded * (P.perAttemptFiles.length + P.perCaseFiles.length) + P.packFiles.length;
export const COMMIT_PATH_COUNT = PACK_FILE_COUNT + P.catalogEdits.length;
export const VERIFIER_KNOWN = P.verifier.known;

/** The pack README, exactly as publishing.py writes it for these numbers. */
export const README_TEXT = [
  `# ${P.pack}`,
  "",
  "Private KubeLLM operator campaign exported as an exploratory evidence pack.",
  "",
  `- Campaign status: **${(CAMPAIGN?.status ?? "completed").toUpperCase()}**.`,
  `- Structured attempts exported: **${P.attempts.recorded} of ${P.attempts.planned} planned**.`,
  `- Case outcomes with configured Ground Truth: **${P.groundTruth.passed} of ${P.groundTruth.known} known**; unknown outcomes remain unavailable.`,
  `- Independent Verifier results recorded: **${VERIFIER_KNOWN}**; agreement with known Ground Truth: **${P.verifier.agrees} of ${P.verifier.comparable} comparable**.`,
  `- Attempts without an exportable structured configuration: **${P.attempts.excluded}**; planned attempts not started: **${P.attempts.unstarted}**.`,
  `- Cases: ${CASES.map((c) => `\`${c}\``).join(", ")}.`,
  `- Techniques: ${P.techniques.map((t) => `\`${t}\``).join(", ")}.`,
  `- Reviewed model identifiers: ${MODELS.map((m) => `\`${m}\``).join(", ")}.`,
  "",
  "Each attempt is stored under its technique as a sanitized structured projection. This exploratory pack is excluded from canonical analysis by the `run_config.archived.json` marker.",
  "",
  "Raw logs, progress traces, prompts, generated commands, free-form results, endpoints, credentials, and private lane details were excluded by `scripts/archive_exploratory_run.py`.",
  "",
].join("\n");

/** The two catalog edits, exactly as publishing.py composes them. */
export const CATALOG_DIFFS: { path: string; how: string; context: string; added: string }[] = [
  {
    path: "data/exploratory/README.md",
    how: "One table row, inserted before the line that begins “New sanitized packs use scripts/archive_exploratory_run.py”.",
    context: "New sanitized packs use `scripts/archive_exploratory_run.py` …",
    added: `| [\`${P.pack}/\`](${P.pack}/) | ${P.attempts.recorded} case outcomes across ${P.attempts.recorded} exported attempts | Operator campaign; ${P.groundTruth.known} configured Ground Truth outcome(s) known; ${P.attempts.excluded} attempt(s) lacked exportable structure and ${P.attempts.unstarted} planned attempt(s) were not started. |`,
  },
  {
    path: "data/README.md",
    how: "One paragraph, appended at the end.",
    context: "(end of file)",
    added: `The [${P.pack}](exploratory/${P.pack}/README.md) operator campaign is an exploratory, sanitized evidence pack; it does not change the canonical benchmark dataset.`,
  },
];

/** Illustrative content: the fields the sanitizer keeps, with sample values. */
export function illustrative(path: string): string | null {
  const attempt = ATTEMPTS.find((a) => path.includes(`attempt-${String(a.seq).padStart(4, "0")}-`)) ?? ATTEMPTS[0];
  const name = path.split("/").pop() ?? "";
  const runId = "2026-09-22T18-27-02";
  const json = (v: unknown) => JSON.stringify(v, null, 2);
  switch (name) {
    case "run_config.archived.json":
      return json({ jobs: 1, run_id: runId, teardown_after_run: true, technique: TECHNIQUE, test_names: [attempt.caseId] });
    case "provenance.archived.json":
      return json({ git_commit: "<40-character commit>", git_dirty: false, run_id: runId });
    case "aggregate.json":
      return json({ errors: 0, failed: 0, generated_at: "2026-09-22T18:29:41.204118", ground_truth_passed: 1, ground_truth_rate: 100.0, passed: 1, tests_with_ground_truth: 1, tests_with_verification: 1, total_cost: 0.0141, total_tests: 1, verified: 1 });
    case "summary.json":
      return json({ debug_self_report: true, duration_s: 137.6, ground_truth_configured: true, ground_truth_passed: true, metrics: { api: { cost: 0.0054, total_tokens: 4070 }, debug: { cost: 0.0036, total_tokens: 17463 }, verification: { cost: 0.0051, total_tokens: 35356 } }, status: "PASS", technique: TECHNIQUE, verified: true });
    case "ground_truth.json": {
      const checks = ((data as unknown as { cases: Record<string, { checks: string[] }> }).cases[attempt.caseId]?.checks ?? []).map((check) => ({ attempts: 1, duration_ms: 420, name: check, status: "PASS" }));
      return json({ checks, passed: true, summary: { ERROR: 0, FAIL: 0, PASS: checks.length, SKIP: 0 }, total_duration_ms: 1260 });
    }
    case "verification_report.meta.json":
      return json({ content_length: 2318, content_sha256: "<64-character digest of the verifier report>", verification_status: true });
    case "config_effective.json":
      return json({ "api-agent": { model: P.models.API }, "debug-agent": { model: P.models.DebugAgent }, "verification-agent": { model: P.models.Verification, temperature: 1 } });
    default:
      return null;
  }
}

/** What each file holds, in a few words. */
export const FILE_NOTE: Record<string, string> = {
  "README.md": "Pack summary written by the publication flow",
  "run_config.archived.json": "Run ID, technique, cases; the .archived name keeps the pack out of canonical analysis",
  "provenance.archived.json": "Run ID, Git commit, dirty flag",
  "aggregate.json": "Counts, rates, cost and token totals",
  "summary.json": "Status, Ground Truth, verifier verdict, timings, per-role metrics",
  "ground_truth.json": "Check names, statuses, timings; no commands or observations",
  "verification_report.meta.json": "Verifier verdict and report fingerprint; no prose",
  "config_effective.json": "Reviewed model IDs and sampling settings per role",
};

// ---------------------------------------------------------------- tree

export interface TreeNode {
  name: string;
  path: string;
  dir: boolean;
  files: number;
  children: TreeNode[];
}

function buildTree(): TreeNode {
  const root: TreeNode = { name: `${P.pack}/`, path: P.destination, dir: true, files: 0, children: [] };
  root.children.push({ name: "README.md", path: `${P.destination}/README.md`, dir: false, files: 1, children: [] });
  const tech: TreeNode = { name: `${TECHNIQUE}/`, path: `${P.destination}/${TECHNIQUE}`, dir: true, files: 0, children: [] };
  for (const a of ATTEMPTS) {
    const base = `${P.destination}/${a.dir}`;
    const caseDir: TreeNode = { name: `${a.caseId}/`, path: `${base}/${a.caseId}`, dir: true, files: P.perCaseFiles.length, children: P.perCaseFiles.map((f) => ({ name: f, path: `${base}/${a.caseId}/${f}`, dir: false, files: 1, children: [] })) };
    tech.children.push({
      name: `${a.dir.split("/")[1]}/`,
      path: base,
      dir: true,
      files: P.perAttemptFiles.length + P.perCaseFiles.length,
      children: [...P.perAttemptFiles.map((f) => ({ name: f, path: `${base}/${f}`, dir: false, files: 1, children: [] })), caseDir],
    });
  }
  tech.files = tech.children.reduce((s, c) => s + c.files, 0);
  root.children.push(tech);
  root.files = tech.files + 1;
  return root;
}

export const TREE = buildTree();

function FileIcon({ name, dir, open }: { name: string; dir: boolean; open?: boolean }) {
  const cls = "size-3.5 shrink-0 text-fg-3";
  if (dir) return open ? <FolderOpen className={cls} strokeWidth={1.75} /> : <Folder className={cls} strokeWidth={1.75} />;
  if (name.endsWith(".json")) return <FileBraces className={cls} strokeWidth={1.75} />;
  if (name.endsWith(".md")) return <FileText className={cls} strokeWidth={1.75} />;
  return <File className={cls} strokeWidth={1.75} />;
}

/** Collapsible file tree; filter matches attempt and case names. */
export function FileTree({ selected, onSelect, filter = "", className, maxHeight = 520 }: { selected?: string; onSelect?: (path: string) => void; filter?: string; className?: string; maxHeight?: number }) {
  const [open, setOpen] = useState<Set<string>>(() => new Set([TREE.path, TREE.children[1].path, TREE.children[1].children[0].path]));
  const q = filter.trim().toLowerCase();
  const toggle = (path: string) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const rows: { node: TreeNode; depth: number; isOpen: boolean }[] = [];
  const walk = (node: TreeNode, depth: number) => {
    const visibleChildren = q && node === TREE.children[1] ? node.children.filter((c) => c.name.includes(q)) : node.children;
    const isOpen = node.dir && (open.has(node.path) || (q !== "" && depth < 2));
    rows.push({ node, depth, isOpen });
    if (isOpen) visibleChildren.forEach((child) => walk(child, depth + 1));
  };
  walk(TREE, 0);

  return (
    <ul role="tree" aria-label="Files in the pack" className={clsx("overflow-auto py-1 font-mono text-[12px]", className)} style={{ maxHeight }}>
      {rows.map(({ node, depth, isOpen }) => (
        <li key={node.path} role="treeitem" aria-expanded={node.dir ? isOpen : undefined} aria-selected={selected === node.path}>
          <button
            type="button"
            onClick={() => (node.dir ? toggle(node.path) : onSelect?.(node.path))}
            className={clsx("flex w-full cursor-pointer items-center gap-1.5 py-[3px] pr-3 text-left", selected === node.path ? "bg-accent-soft text-fg" : "text-fg-2 hover:bg-surface-2 hover:text-fg")}
            style={{ paddingLeft: 8 + depth * 12 }}
            title={node.dir ? node.name : `${node.name}: ${FILE_NOTE[node.name] ?? ""}`}
          >
            {node.dir ? <ChevronRight className={clsx("size-3 shrink-0 text-fg-3 transition-transform", isOpen && "rotate-90")} strokeWidth={2} /> : <span className="w-3 shrink-0" />}
            <FileIcon name={node.name} dir={node.dir} open={isOpen} />
            <span className="min-w-0 truncate">{node.name}</span>
            {node.dir && <span className="num ml-auto shrink-0 pl-2 font-sans text-[11px] text-fg-3">{count(node.files)}</span>}
          </button>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------- preview expiry

let preparedAt = Date.now();
const expiryListeners = new Set<() => void>();
export const preview = {
  refresh() {
    preparedAt = Date.now();
    expiryListeners.forEach((l) => l());
  },
};

/** Real-time countdown of the 30-minute preview token. */
export function usePreviewExpiry() {
  const prepared = useSyncExternalStore(
    (l) => {
      expiryListeners.add(l);
      return () => expiryListeners.delete(l);
    },
    () => preparedAt,
  );
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const left = prepared + PREVIEW_TTL_MIN * 60_000 - now;
  return { left, expired: left <= 0, label: countdown(left), prepared };
}

// ---------------------------------------------------------------- publish job

export const PUBLISH_STEPS = [
  { label: "Verifying reviewed files and Git target.", detail: "Preview token, every file hash, both catalog hashes, the branch, and HEAD must match the review.", ms: 1500 },
  { label: "Adding only the reviewed export paths.", detail: `git add -- ${count(COMMIT_PATH_COUNT)} literal paths`, ms: 1100 },
  { label: "Creating a commit containing the reviewed result files.", detail: `git commit --only · “${COMMIT_MESSAGE}”`, ms: 1000 },
  ...(PUSHES_AFTER_COMMIT ? [{ label: "Pushing the export commit to the configured upstream.", detail: `git push · ${P.target.branch} → ${P.target.upstream}`, ms: 2200 }] : []),
];
export const PUBLISH_DONE = PUSHES_AFTER_COMMIT ? "Sanitized results were committed and pushed." : "Sanitized results were committed locally.";

export type JobPhase = "idle" | "running" | "done";

/** A short demo publication job that walks the real step labels. */
export function usePublishJob() {
  const [phase, setPhase] = useState<JobPhase>("idle");
  const [step, setStep] = useState(0);
  const [startedAt, setStartedAt] = useState(0);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const start = () => {
    setPhase("running");
    setStep(0);
    setStartedAt(Date.now());
    let i = 0;
    const next = () => {
      timer.current = window.setTimeout(() => {
        i += 1;
        if (i >= PUBLISH_STEPS.length) setPhase("done");
        else {
          setStep(i);
          next();
        }
      }, PUBLISH_STEPS[i].ms);
    };
    next();
  };
  const reset = () => {
    window.clearTimeout(timer.current);
    setPhase("idle");
    setStep(0);
  };
  return { phase, step, startedAt, start, reset };
}

export function PublishSteps({ phase, step, className }: { phase: JobPhase; step: number; className?: string }) {
  const message = phase === "done" ? PUBLISH_DONE : phase === "running" ? PUBLISH_STEPS[step].label : "";
  return (
    <div className={className}>
      <ol className="grid gap-2">
        {PUBLISH_STEPS.map((s, i) => {
          const state = phase === "done" || i < step ? "done" : phase === "running" && i === step ? "running" : "pending";
          return (
            <li key={s.label} className="grid grid-cols-[16px_minmax(0,1fr)] gap-x-2.5 text-[12.5px]">
              <span className="translate-y-[2px]">
                <CheckMark level={state === "done" ? "pass" : undefined} running={state === "running"} pending={state === "pending"} />
              </span>
              <span className="min-w-0">
                <span className={state === "pending" ? "text-fg-3" : "text-fg"}>{s.label}</span>
                {state !== "pending" && <span className="mt-0.5 block font-mono text-[11.5px] break-words text-fg-3">{s.detail}</span>}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="sr-only" role="status" aria-live="polite">
        {message}
      </p>
    </div>
  );
}

export function useFilteredCount(filter: string) {
  return useMemo(() => (filter.trim() ? ATTEMPTS.filter((a) => a.dir.includes(filter.trim().toLowerCase())).length : ATTEMPTS.length), [filter]);
}

export const campaignLine = CAMPAIGN ? `${CAMPAIGN.title} · ${CAMPAIGN.status} ${CAMPAIGN.finishedAt ? stamp(Date.parse(CAMPAIGN.finishedAt)) : ""} UTC` : SHORT_ID;
