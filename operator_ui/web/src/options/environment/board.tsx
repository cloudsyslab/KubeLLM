import clsx from "clsx";
import { Boxes, Container, Database, Folder, HardDrive, ListChecks, Package, Plug, Server, Wrench, type LucideIcon } from "lucide-react";
import { Tip } from "@/components/ui";
import { CheckMark, LANE, TTL_MS, countdown, isRepairable, ms, type ActiveRun, type CheckLevel, type Freshness, type ReadinessCheck } from "./readiness";

// The readiness checks regrouped by the dependency they prove, for the board.

export interface Dep {
  id: string;
  name: string;
  identity: string;
  icon: LucideIcon;
  checks: string[];
  zone: "workspace" | "host" | "lane";
}

export const DEPS: Dep[] = [
  { id: "repo", name: "Repository", identity: "KubeLLM checkout", icon: Folder, checks: ["repo_checkout"], zone: "workspace" },
  { id: "python", name: "Python environment", identity: ".venv · pinned lock", icon: Package, checks: ["venv_python", "python_imports", "pytest"], zone: "workspace" },
  { id: "runner", name: "Runner gates", identity: "runner.py · 27 cases", icon: ListChecks, checks: ["static_list", "static_truth", "config_validity", "lab_lane"], zone: "workspace" },
  { id: "providers", name: "Model providers", identity: "OpenAI API · Ollama :11434", icon: Plug, checks: ["providers_api", "providers_ollama"], zone: "host" },
  { id: "storage", name: "Storage", identity: ".local/ run roots · Docker data root", icon: HardDrive, checks: ["artifacts_paths", "artifacts_disk"], zone: "host" },
  { id: "docker", name: "Docker engine", identity: "host daemon", icon: Container, checks: ["docker_engine"], zone: "host" },
  { id: "cluster", name: "Cluster", identity: `minikube profile ${LANE.profile}`, icon: Boxes, checks: ["minikube_status", "cluster_access", "kubectl", "kubeconfig_owner"], zone: "lane" },
  { id: "rag", name: "RAG API", identity: LANE.ragApi.replace("http://", ""), icon: Server, checks: ["rag_lane", "rag_api"], zone: "lane" },
  { id: "pgvector", name: "pgvector", identity: LANE.pgvector, icon: Database, checks: ["pgvector_owner", "db_connectivity"], zone: "lane" },
];

export const ZONES = [
  { id: "lane", label: "Lane services", note: "Owned by minh-lane; preparation may start them." },
  { id: "host", label: "Host", note: "Shared with other researchers; read only." },
  { id: "workspace", label: "Workspace", note: "This checkout and the runner's own gates." },
] as const;

export const depOfCheck = (checkId: string) => DEPS.find((d) => d.checks.includes(checkId));

export type DepState = { level?: CheckLevel; running: boolean; pending: boolean; done: ReadinessCheck[]; all: ReadinessCheck[] };

/** A dependency's checks in the run being shown (or streaming), and its worst level once all have run. */
export function depState(dep: Dep, source: ReadinessCheck[], done: ReadinessCheck[], active?: ActiveRun): DepState {
  const all = dep.checks.map((id) => source.find((c) => c.id === id)).filter((c): c is ReadinessCheck => Boolean(c));
  const finished = all.filter((c) => done.some((d) => d.id === c.id)).map((c) => done.find((d) => d.id === c.id)!);
  const running = Boolean(active?.current && dep.checks.includes(active.current.id));
  const level: CheckLevel | undefined = finished.length === all.length && all.length ? (finished.find((c) => c.level === "block")?.level ?? finished.find((c) => c.level === "warn")?.level ?? "pass") : undefined;
  return { level, running, pending: !running && finished.length < all.length, done: finished, all };
}

const WORD: Record<CheckLevel, string> = { pass: "Healthy", warn: "Warning", block: "Blocked", skip: "Skipped" };

/** The 20-minute freshness window as a ring; check progress while a run streams. */
export function Ring({ fresh }: { fresh: Freshness }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const value = fresh.state === "fresh" ? fresh.left / TTL_MS : fresh.state === "checking" ? fresh.active.done.length / Math.max(1, fresh.active.total) : 0;
  const tone = fresh.state === "checking" ? "var(--accent)" : fresh.state === "fresh" ? (value < 0.25 ? "var(--warn)" : "var(--fg)") : "var(--warn)";
  return (
    <div className="relative grid size-[92px] shrink-0 place-items-center">
      <svg viewBox="0 0 80 80" className="absolute inset-0 -rotate-90" aria-hidden>
        <circle cx="40" cy="40" r={r} fill="none" stroke="var(--surface-3)" strokeWidth="4" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={tone} strokeWidth="4" strokeLinecap="round" strokeDasharray={`${value * c} ${c}`} className="transition-[stroke-dasharray] duration-700" />
      </svg>
      <div className="grid text-center">
        <span className="num text-[17px] leading-none font-medium">
          {fresh.state === "fresh" ? countdown(fresh.left) : fresh.state === "checking" ? `${fresh.active.done.length}/${fresh.active.total}` : "0:00"}
        </span>
        <span className="mt-1 text-[10.5px] text-fg-3">{fresh.state === "checking" ? "checks" : "fresh"}</span>
      </div>
    </div>
  );
}

export function DepCard({ dep, state, selected, onSelect }: { dep: Dep; state: DepState; selected: boolean; onSelect: () => void }) {
  const Icon = dep.icon;
  const failing = state.done.filter((c) => c.level === "warn" || c.level === "block");
  const repairable = state.all.some(isRepairable);
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={clsx(
        "grid w-full cursor-pointer content-start gap-2 rounded-lg border p-3 text-left transition-colors",
        selected ? "border-accent-line bg-accent-soft" : state.running ? "border-accent-line bg-surface" : failing.length ? "border-warn/40 bg-surface hover:border-warn/60" : "border-line bg-surface hover:border-line-strong",
      )}
    >
      <div className="flex items-center gap-2.5">
        <span className={clsx("grid size-7 shrink-0 place-items-center rounded-md border", failing.length ? "border-warn/40 text-warn" : "border-line text-fg-2")}>
          <Icon className="size-3.5" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium text-fg">{dep.name}</div>
          <div className="ident truncate text-[11.5px] text-fg-3">{dep.identity}</div>
        </div>
      </div>
      {failing.length > 0 && <p className="text-[12px] leading-snug text-fg-2">{failing[0].detail}</p>}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-fg-3">
        <span className={clsx("inline-flex items-center gap-1.5 text-[12px]", state.running ? "text-accent" : state.pending ? "text-fg-3" : state.level === "pass" ? "text-fg-2" : "text-warn")}>
          <CheckMark level={state.level} running={state.running} pending={state.pending} className="size-3" />
          {state.running ? "Checking" : state.pending ? "Pending" : state.level ? WORD[state.level] : "—"}
        </span>
        <span className="num">
          {state.done.length}/{state.all.length}
          {state.done.length ? ` · ${ms(state.done.reduce((s, c) => s + c.ms, 0))}` : ""}
        </span>
        {repairable && (
          <Tip content="Prepare environment may repair this dependency.">
            <span className="ml-auto inline-flex items-center gap-1">
              <Wrench className="size-3" strokeWidth={1.75} /> Repairable
            </span>
          </Tip>
        )}
      </div>
    </button>
  );
}
