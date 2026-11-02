import clsx from "clsx";
import { ChevronRight, Radio, TriangleAlert, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Tag, Tip } from "@/components/ui";
import { DEPS, DepCard, Ring, ZONES, depOfCheck, depState, type Dep } from "./board";
import { HistoryList, RunSteps, rowIdOf, samePick, type Selected } from "./steps";
import { Terminal, type TerminalSubject } from "./terminal";
import {
  CheckMark,
  KIND_WORD,
  LANE,
  LaneFacts,
  LiveAnnouncer,
  READINESS_TTL_MIN,
  RepairScope,
  RunActions,
  ScenarioSwitch,
  StatusWord,
  ago,
  freshnessLine,
  ms,
  repairsForRun,
  stamp,
  summarize,
  useFreshness,
  useReducedMotion,
  type ActiveRun,
  type ReadinessCheck,
  type ReadinessRun,
} from "./readiness";

// Environment: the health board over the lane's dependencies, with the run
// beneath it as CI steps and each step's terminal output. A card selects its
// dependency's most telling check; a step opens its terminal beside the steps
// (wide screens) or under the row (narrow ones). While a run streams, the
// terminal follows the running check unless a step is pinned.

/** Which dependency each repair works on. */
const REPAIR_DEP: Record<string, string> = { minikube_profile: "cluster", kubeconfig: "cluster", rag_api: "rag", pgvector: "pgvector", virtual_environment: "python", prepare_env: "providers" };

function useWide(query = "(min-width: 1024px)") {
  const [wide, setWide] = useState(() => typeof window !== "undefined" && window.matchMedia?.(query).matches === true);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return;
    const sync = () => setWide(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, [query]);
  return wide;
}

/** Re-renders on an interval while `on`, for streaming output. */
function useTicker(on: boolean, every = 120) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!on) return;
    const id = window.setInterval(() => setTick((v) => v + 1), every);
    return () => window.clearInterval(id);
  }, [on, every]);
}

const isProblem = (c: ReadinessCheck) => c.level === "warn" || c.level === "block";

/** The step a run opens on: its first problem, else the lane's cluster status. */
function defaultPick(checks: ReadinessCheck[]): Selected | undefined {
  const check = checks.find(isProblem) ?? checks.find((c) => c.id === "minikube_status") ?? checks[0];
  return check && { kind: "check", id: check.id };
}

/** The live step: the running repair or check, else the last one finished. */
function livePick(active: ActiveRun): Selected | undefined {
  if (active.currentRepair) return { kind: "repair", name: active.currentRepair.name };
  if (active.current) return { kind: "check", id: active.current.id };
  const last = active.done[active.done.length - 1] ?? active.target[0];
  return last && { kind: "check", id: last.id };
}

/** A dependency's most telling check: its first problem, the running one, or its first. */
function pickForDep(dep: Dep, source: ReadinessCheck[], done: ReadinessCheck[], active?: ActiveRun): Selected {
  const finished = dep.checks.map((id) => done.find((c) => c.id === id)).filter((c): c is ReadinessCheck => Boolean(c));
  const id = finished.find(isProblem)?.id ?? (active?.current && dep.checks.includes(active.current.id) ? active.current.id : undefined) ?? dep.checks.find((c) => source.some((s) => s.id === c)) ?? dep.checks[0];
  return { kind: "check", id };
}

const sumMs = (checks: ReadinessCheck[]) => checks.reduce((s, c) => s + c.ms, 0);

export default function LaneHealth() {
  const { fresh, runs, latest, active, now } = useFreshness();
  const wide = useWide();
  const reduced = useReducedMotion();
  const [viewId, setViewId] = useState<string | undefined>();
  const [pinned, setPinned] = useState<Selected | undefined>();
  const [scopeOpen, setScopeOpen] = useState(false);
  const [scrollTo, setScrollTo] = useState<string | undefined>();

  const view: ReadinessRun | undefined = active ? undefined : (runs.find((r) => r.id === viewId) ?? latest);
  const source = active ? active.target : (view?.checks ?? []);
  const done = active ? active.done : source;
  const s = view ? summarize(view.checks) : undefined;
  const disk = (view?.checks ?? []).find((c) => c.id === "artifacts_disk" && c.level === "warn");
  const needed = view ? repairsForRun(view.checks) : [];

  // A new run follows its live step.
  useEffect(() => setPinned(undefined), [active?.id]);

  // ---------------------------------------------------------- which step shows
  const resolve = (pick?: Selected): { subject: TerminalSubject; offset: number; progress?: number; pending?: boolean } | undefined => {
    if (!pick) return undefined;
    if (pick.kind === "check") {
      const index = source.findIndex((c) => c.id === pick.id);
      if (index < 0) return undefined;
      const offset = sumMs(source.slice(0, index));
      const finished = done.find((c) => c.id === pick.id);
      if (finished) return { subject: { kind: "check", check: finished }, offset };
      const running = active?.current?.id === pick.id;
      return { subject: { kind: "check", check: source[index] }, offset, progress: running ? progressOf(`${active!.id}-${active!.pass}-${pick.id}`, source[index].ms) : undefined, pending: !running };
    }
    const repairs = active ? active.repairs : (view?.repairs ?? []);
    const beforeRepairs = sumMs(source.slice(0, Math.max(0, source.findIndex((c) => c.id === "kubeconfig_owner"))));
    const index = repairs.findIndex((r) => r.name === pick.name);
    if (index >= 0) return { subject: { kind: "repair", repair: repairs[index] }, offset: beforeRepairs + repairs.slice(0, index).reduce((t, r) => t + r.ms, 0) };
    if (active?.currentRepair?.name === pick.name) {
      return { subject: { kind: "repair", repair: active.currentRepair }, offset: beforeRepairs + repairs.reduce((t, r) => t + r.ms, 0), progress: progressOf(`${active.id}-repair-${pick.name}`, active.currentRepair.ms) };
    }
    return undefined;
  };

  // When the running step began, to reveal its output over its duration.
  const started = useRef<{ key: string; at: number }>({ key: "", at: 0 });
  function progressOf(key: string, duration: number) {
    if (started.current.key !== key) started.current = { key, at: Date.now() };
    return Math.min(0.97, (Date.now() - started.current.at) / Math.max(1, duration));
  }
  useTicker(Boolean(active));

  const live = active ? livePick(active) : undefined;
  const fallback = active ? live : defaultPick(source);
  const shown = resolve(pinned) ? pinned : fallback;
  const terminal = resolve(shown);
  const following = Boolean(active && !pinned);

  const selectedDepId = shown?.kind === "check" ? depOfCheck(shown.id)?.id : shown ? REPAIR_DEP[shown.name] : undefined;
  const focus = new Set(DEPS.find((d) => d.id === selectedDepId)?.checks ?? []);

  const choose = (pick: Selected, scroll = false) => {
    setPinned(samePick(pick, live) && active ? undefined : pick);
    if (scroll) setScrollTo(rowIdOf(pick));
  };

  // A card brings its step (and, on narrow screens, the terminal under it) into view.
  useEffect(() => {
    if (!scrollTo) return;
    const id = window.requestAnimationFrame(() => {
      document.getElementById(scrollTo)?.scrollIntoView({ block: wide ? "center" : "start", behavior: reduced ? "auto" : "smooth" });
      setScrollTo(undefined);
    });
    return () => window.cancelAnimationFrame(id);
  }, [scrollTo, wide, reduced]);

  const terminalNode = terminal && <Terminal key={shown ? rowIdOf(shown) : "none"} subject={terminal.subject} offset={terminal.offset} progress={terminal.progress} pending={terminal.pending} />;

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex justify-end">
        <ScenarioSwitch />
      </div>

      {/* Lane readiness: the freshness ring, the lane, and the two actions. */}
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
          <div className="grid gap-2 text-[12.5px]">
            <button type="button" aria-expanded={scopeOpen} onClick={() => setScopeOpen(!scopeOpen)} className="flex cursor-pointer items-center gap-1 justify-self-start text-fg-3 hover:text-fg">
              <ChevronRight className={clsx("size-3.5 transition-transform", scopeOpen && "rotate-90")} strokeWidth={2} />
              What preparation may change
            </button>
            {scopeOpen && <RepairScope highlight={needed} />}
          </div>
        </div>
      </section>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* The board: one card per dependency, in three zones. */}
        <div className="order-1 grid gap-5">
          {ZONES.map((zone) => (
            <section key={zone.id} aria-label={zone.label} className="grid gap-2">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <h3 className="text-[13.5px] font-medium">{zone.label}</h3>
                <span className="text-[12px] text-fg-3">{zone.note}</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {DEPS.filter((d) => d.zone === zone.id).map((dep) => (
                  <DepCard key={dep.id} dep={dep} state={depState(dep, source, done, active)} selected={selectedDepId === dep.id} onSelect={() => choose(pickForDep(dep, source, done, active), true)} />
                ))}
              </div>
            </section>
          ))}
        </div>

        <aside className="order-3 rounded-lg border border-line bg-surface lg:order-2" aria-label="Preflight history">
          <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <div>
              <h3 className="text-[13.5px] font-medium">History</h3>
              <p className="mt-0.5 text-[12px] text-fg-3">Preflight and preparation on this lane.</p>
            </div>
            <Tag tone="accent">Demo</Tag>
          </header>
          <HistoryList
            runs={runs}
            selected={view?.id}
            onSelect={(id) => {
              setViewId(id);
              setPinned(undefined);
            }}
          />
          {view && s && !active && (
            <p className="border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
              Showing the {KIND_WORD[view.kind].toLowerCase()} from {stamp(view.finishedAt)} UTC, {ago(now - view.finishedAt)}: {s.pass} passed, {s.warn} warning, {s.block} blocked.
            </p>
          )}
        </aside>

        {/* The run as CI steps, with the selected step's terminal. */}
        <section className="order-2 min-w-0 rounded-lg border border-line bg-surface lg:order-3 lg:col-span-2" aria-label="Checks">
          <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-line px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <h3 className="truncate text-[13.5px] font-medium">
                {active ? `${KIND_WORD[active.kind]} · ${active.pass === "recheck" ? "recheck" : active.kind === "prepare" ? "repair-safe" : "check-only"}` : view ? `${KIND_WORD[view.kind]} · ${view.mode}` : "No preflight yet"}
              </h3>
              <Tag tone="accent">Demo</Tag>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="num text-[12px] text-fg-3">
                {active
                  ? `${active.done.length}/${active.total} · ${ms(Math.max(0, now - active.startedAt))}`
                  : view && s
                    ? `${s.pass} passed${s.warn ? ` · ${s.warn} warning` : ""}${s.block ? ` · ${s.block} blocked` : ""} · ${ms(view.finishedAt - view.startedAt)} · ${ago(now - view.finishedAt)}`
                    : ""}
              </span>
              {active && (
                following ? (
                  <span className="inline-flex items-center gap-1.5 text-[12px] text-accent">
                    <Radio className="size-3.5" strokeWidth={1.75} /> Following the running check
                  </span>
                ) : (
                  <button type="button" onClick={() => setPinned(undefined)} className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12px] text-fg hover:bg-surface-2">
                    <Radio className="size-3.5" strokeWidth={1.75} /> Back to live
                  </button>
                )
              )}
            </div>
          </header>
          {active && <p className="border-b border-line px-4 py-2 font-mono text-[12px] text-fg-2">{active.label}</p>}
          {disk && (
            <div className="flex items-start gap-2.5 border-b border-line bg-warn-soft px-4 py-2.5 text-[12.5px]">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-warn" strokeWidth={2} />
              <span className="text-fg-2">
                <span className="font-medium text-warn">Docker data root.</span> {disk.detail} Free space on the lab before preparing a stopped lane.
              </span>
            </div>
          )}
          {view?.status === "BLOCKED" && needed.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-line px-4 py-2.5 text-[12.5px] text-fg-2">
              <Wrench className="size-3.5 text-fg-3" strokeWidth={1.75} />
              Preparation can address {needed.length} of the failing areas:
              {needed.map((n) => (
                <Tip key={n} content="See What preparation may change, above.">
                  <span tabIndex={0} className="ident text-fg">
                    {n}
                  </span>
                </Tip>
              ))}
            </div>
          )}
          <div className={clsx(wide && "grid grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]")}>
            <div className={clsx("min-w-0 py-1", wide && "border-r border-line")}>
              <RunSteps
                key={active ? `${active.id}-${active.pass}` : view?.id}
                run={view}
                active={active}
                selected={shown}
                onSelect={(pick) => choose(pick)}
                focus={focus}
                inline={wide ? undefined : () => terminalNode && <div className="px-3 pt-1 pb-3">{terminalNode}</div>}
              />
            </div>
            {wide && (
              <div className="min-w-0 p-3">
                <div className="sticky top-[72px]">{terminalNode ?? <p className="py-10 text-center text-[12.5px] text-fg-3">Select a step to see its output.</p>}</div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
