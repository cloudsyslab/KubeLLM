import clsx from "clsx";
import { Boxes, Container, Database, Folder, HardDrive, ListChecks, Package, Plug, Server, Wrench, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { Tag, Tip } from "@/components/ui";
import {
  CheckMark,
  KIND_WORD,
  LANE,
  LaneFacts,
  LiveAnnouncer,
  READINESS_TTL_MIN,
  REPAIRS,
  RunActions,
  ScenarioSwitch,
  StatusWord,
  TTL_MS,
  ago,
  countdown,
  freshnessLine,
  isRepairable,
  ms,
  stamp,
  summarize,
  useFreshness,
  type CheckLevel,
  type Freshness,
  type ReadinessCheck,
} from "./readiness";

// The same 21 checks, regrouped by the dependency they prove.
interface Dep {
  id: string;
  name: string;
  identity: string;
  icon: LucideIcon;
  checks: string[];
  zone: "workspace" | "host" | "lane";
}

const DEPS: Dep[] = [
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

const ZONES = [
  { id: "lane", label: "Lane services", note: "Owned by minh-lane; preparation may start them." },
  { id: "host", label: "Host", note: "Shared with other researchers; read only." },
  { id: "workspace", label: "Workspace", note: "This checkout and the runner's own gates." },
] as const;

type DepState = { level?: CheckLevel; running: boolean; pending: boolean; done: ReadinessCheck[]; all: ReadinessCheck[] };

const WORD: Record<CheckLevel, string> = { pass: "Healthy", warn: "Warning", block: "Blocked", skip: "Skipped" };

function Ring({ fresh }: { fresh: Freshness }) {
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

function DepCard({ dep, state, selected, onSelect }: { dep: Dep; state: DepState; selected: boolean; onSelect: () => void }) {
  const Icon = dep.icon;
  const failing = state.done.filter((c) => c.level === "warn" || c.level === "block");
  const repairable = state.all.some(isRepairable);
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={clsx(
        "grid w-full cursor-pointer gap-2 rounded-lg border p-3 text-left transition-colors",
        selected ? "border-accent-line bg-accent-soft" : state.running ? "border-accent-line bg-surface" : failing.length ? "border-warn/40 bg-surface" : "border-line bg-surface hover:border-line-strong",
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

function DepDetail({ dep, state }: { dep: Dep; state: DepState }) {
  const repairs = REPAIRS.filter((r) => r.checks.some((id) => dep.checks.includes(id)));
  return (
    <div className="grid gap-4">
      <div>
        <div className="label">{ZONES.find((z) => z.id === dep.zone)?.label}</div>
        <h3 className="mt-1 text-[15px] font-medium">{dep.name}</h3>
        <div className="ident text-[12px] text-fg-3">{dep.identity}</div>
      </div>
      <ul className="grid gap-2.5">
        {state.all.map((check) => {
          const done = state.done.find((c) => c.id === check.id);
          return (
            <li key={check.id} className="grid grid-cols-[16px_minmax(0,1fr)_auto] items-baseline gap-x-2.5 text-[12.5px]">
              <span className="translate-y-[2px]">
                <CheckMark level={done?.level} pending={!done} />
              </span>
              <span className="min-w-0">
                <span className={clsx(check.group === "live" || check.group === "static" ? "ident" : "", done ? "text-fg" : "text-fg-3")}>{check.label}</span>
                {done && <span className={clsx("mt-0.5 block leading-snug", done.level === "pass" ? "text-fg-3" : "text-fg-2")}>{done.detail}</span>}
              </span>
              <span className="num text-[11.5px] text-fg-3">{done ? ms(done.ms) : ""}</span>
            </li>
          );
        })}
      </ul>
      {repairs.length > 0 ? (
        <div className="grid gap-2 border-t border-line pt-3">
          <div className="label !text-[10px]">Preparation may</div>
          {repairs.map((r) => (
            <div key={r.name} className="grid gap-0.5 text-[12.5px]">
              <span className="text-fg-2">{r.does}</span>
              <span className="text-fg-3">{r.limit}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="border-t border-line pt-3 text-[12.5px] text-fg-3">Preparation does not change this dependency. Fix it on the lab, then run preflight.</p>
      )}
    </div>
  );
}

export default function HealthBoard() {
  const { fresh, runs, latest, active, now } = useFreshness();
  const [selected, setSelected] = useState<string>("cluster");
  const [viewId, setViewId] = useState<string | undefined>();
  const view = active ? undefined : (runs.find((r) => r.id === viewId) ?? latest);
  const source = active ? active.target : (view?.checks ?? []);
  const done = active ? active.done : source;

  const stateOf = (dep: Dep): DepState => {
    const all = dep.checks.map((id) => source.find((c) => c.id === id)).filter((c): c is ReadinessCheck => Boolean(c));
    const finished = all.filter((c) => done.some((d) => d.id === c.id)).map((c) => done.find((d) => d.id === c.id)!);
    const running = Boolean(active?.current && dep.checks.includes(active.current.id));
    const level: CheckLevel | undefined = finished.length === all.length && all.length ? (finished.find((c) => c.level === "block")?.level ?? finished.find((c) => c.level === "warn")?.level ?? "pass") : undefined;
    return { level, running, pending: !running && finished.length < all.length, done: finished, all };
  };
  const selectedDep = DEPS.find((d) => d.id === selected)!;
  const s = view ? summarize(view.checks) : undefined;

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex justify-end">
        <ScenarioSwitch />
      </div>
      <section className="grid gap-5 rounded-lg border border-line bg-surface p-4 sm:p-5 md:grid-cols-[auto_minmax(0,1fr)] xl:grid-cols-[auto_minmax(0,1.2fr)_minmax(0,1fr)]" aria-label="Lane readiness">
        <div className="flex items-center gap-4">
          <Ring fresh={fresh} />
          <div className="grid gap-1">
            <StatusWord fresh={fresh} className="text-[16px]" />
            <span className="text-[12.5px] text-fg-3">{READINESS_TTL_MIN}-minute window</span>
            {active && <span className="font-mono text-[11.5px] text-fg-2">{active.label}</span>}
          </div>
        </div>
        <div className="grid content-start gap-2">
          <div className="flex items-center gap-2">
            <span className="label">Lane</span>
            <span className="ident text-[13px] text-fg">{LANE.profile}</span>
            <Tag>Private</Tag>
          </div>
          <LaneFacts dense />
        </div>
        <div className="grid content-start gap-3 md:col-span-2 xl:col-span-1">
          <p className="text-[12.5px] text-fg-2">{freshnessLine(fresh)}</p>
          <RunActions />
          {(active?.kind === "prepare" ? active.repairs : view?.kind === "prepare" ? view.repairs : []).length > 0 ? (
            <div className="grid gap-1.5 rounded-md border border-line px-3 py-2">
              <div className="label !text-[10px]">{active ? "Preparation so far" : `Preparation · ${stamp(view!.finishedAt)} UTC`}</div>
              <ul className="grid gap-1.5">
                {(active?.kind === "prepare" ? active.repairs : (view?.repairs ?? [])).map((r) => (
                  <li key={r.name} className="grid grid-cols-[16px_minmax(0,1fr)] gap-x-2 text-[12px]">
                    <span className="translate-y-[2px]">
                      <CheckMark level={r.ok ? "pass" : "block"} />
                    </span>
                    <span>
                      <span className="text-fg">{r.label}</span> <span className={r.ok ? "text-fg-3" : "text-warn"}>{r.message}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-[12px] text-fg-3">Preflight only reads. Preparation may start this lane's cluster profile, RAG API, and pgvector, refresh its kubeconfig, and install pinned Python packages, then rechecks.</p>
          )}
        </div>
      </section>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_288px] xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-5">
          {ZONES.map((zone) => (
            <section key={zone.id} aria-label={zone.label} className="grid gap-2">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <h3 className="text-[13.5px] font-medium">{zone.label}</h3>
                <span className="text-[12px] text-fg-3">{zone.note}</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {DEPS.filter((d) => d.zone === zone.id).map((dep) => (
                  <DepCard key={dep.id} dep={dep} state={stateOf(dep)} selected={selected === dep.id} onSelect={() => setSelected(dep.id)} />
                ))}
              </div>
            </section>
          ))}
        </div>
        <aside className="grid gap-4 lg:sticky lg:top-[72px]">
          <div className="rounded-lg border border-line bg-surface p-4">
            <DepDetail dep={selectedDep} state={stateOf(selectedDep)} />
          </div>
          <div className="rounded-lg border border-line bg-surface p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="label">Recent results</span>
              <Tag tone="accent">Demo</Tag>
            </div>
            <ol className="grid gap-1">
              {runs.slice(0, 6).map((run) => {
                const on = !active && view?.id === run.id;
                return (
                  <li key={run.id}>
                    <button type="button" aria-pressed={on} onClick={() => setViewId(run.id)} className={clsx("flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12.5px]", on ? "bg-accent-soft" : "hover:bg-surface-2")}>
                      <CheckMark level={run.status === "READY" ? "pass" : "block"} />
                      <span className={run.status === "BLOCKED" ? "text-warn" : "text-fg"}>{run.status === "READY" ? "Ready" : "Blocked"}</span>
                      <span className="text-fg-3">{KIND_WORD[run.kind]}</span>
                      <span className="num ml-auto text-[11.5px] text-fg-3">{stamp(run.finishedAt)}</span>
                    </button>
                  </li>
                );
              })}
            </ol>
            {view && s && !active && (
              <p className="mt-2 border-t border-line pt-2 text-[12px] text-fg-3">
                Cards show the {KIND_WORD[view.kind].toLowerCase()} from {stamp(view.finishedAt)} UTC, {ago(now - view.finishedAt)}: {s.pass} passed, {s.warn} warning, {s.block} blocked.
              </p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
