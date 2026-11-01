import clsx from "clsx";
import { ChevronRight, TriangleAlert, Wrench } from "lucide-react";
import { useState } from "react";
import { Tag, Tip } from "@/components/ui";
import {
  CheckMark,
  FreshnessBar,
  KIND_WORD,
  LANE,
  LaneFacts,
  LiveAnnouncer,
  RepairScope,
  RunActions,
  ScenarioSwitch,
  StatusWord,
  ago,
  countdown,
  freshnessLine,
  groupChecks,
  isRepairable,
  ms,
  repairsForRun,
  stamp,
  summarize,
  useFreshness,
  type ActiveRun,
  type ReadinessCheck,
  type ReadinessRun,
  type RepairResult,
} from "./readiness";

function CheckRow({ check, running, pending }: { check: ReadinessCheck; running?: boolean; pending?: boolean }) {
  const mono = check.group === "live" || check.group === "static";
  return (
    <li className={clsx("grid grid-cols-[16px_minmax(0,1fr)_auto] items-baseline gap-x-3 py-1.5 pr-4 pl-10 text-[12.5px]", running && "bg-accent-soft/50")}>
      <span className="translate-y-[2px]">
        <CheckMark level={check.level} running={running} pending={pending} />
      </span>
      <span className="min-w-0">
        <span className={clsx(mono ? "ident" : "", pending ? "text-fg-3" : "text-fg")}>{check.label}</span>
        {!pending && !running && (
          <span className={clsx("mt-0.5 block leading-snug", check.level === "pass" ? "text-fg-3" : "text-fg-2")}>
            {check.detail}
            {check.level !== "pass" && isRepairable(check) && (
              <span className="ml-2 inline-flex items-center gap-1 text-fg-3">
                <Wrench className="size-3" strokeWidth={1.75} /> preparation may repair
              </span>
            )}
          </span>
        )}
      </span>
      <span className="num text-[11.5px] text-fg-3">{pending ? "" : running ? "…" : ms(check.ms)}</span>
    </li>
  );
}

function RepairRow({ repair, running }: { repair: RepairResult; running?: boolean }) {
  return (
    <li className={clsx("grid grid-cols-[16px_minmax(0,1fr)_auto] items-baseline gap-x-3 py-1.5 pr-4 pl-10 text-[12.5px]", running && "bg-accent-soft/50")}>
      <span className="translate-y-[2px]">{running ? <CheckMark running /> : <CheckMark level={repair.ok ? "pass" : "block"} />}</span>
      <span className="min-w-0">
        <span className="text-fg">{repair.label}</span> <span className="ident text-[11px] text-fg-3">{repair.name}</span>
        {!running && <span className={clsx("mt-0.5 block leading-snug", repair.ok ? "text-fg-3" : "text-warn")}>{repair.message}</span>}
      </span>
      <span className="num text-[11.5px] text-fg-3">{running ? "…" : ms(repair.ms)}</span>
    </li>
  );
}

function StepGroup({ title, meta, worst, running, pending, open, onToggle, children }: { title: string; meta: string; worst?: ReadinessCheck["level"]; running?: boolean; pending?: boolean; open: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <li className="border-t border-line first:border-t-0">
      <button type="button" aria-expanded={open} onClick={onToggle} className="grid w-full cursor-pointer grid-cols-[14px_16px_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2 text-left hover:bg-surface-2">
        <ChevronRight className={clsx("size-3.5 text-fg-3 transition-transform", open && "rotate-90")} strokeWidth={2} />
        <CheckMark level={worst} running={running} pending={pending} />
        <span className={clsx("truncate text-[13px]", pending ? "text-fg-3" : "text-fg")}>{title}</span>
        <span className="num text-[11.5px] text-fg-3">{meta}</span>
      </button>
      {open && <ul className="pb-1.5">{children}</ul>}
    </li>
  );
}

function RunSteps({ run, active }: { run?: ReadinessRun; active?: ActiveRun }) {
  const [toggled, setToggled] = useState<Record<string, boolean>>({});
  const live = active !== undefined;
  const allGroups = groupChecks(live ? active.target : (run?.checks ?? []));
  const repairs = live ? active.repairs : (run?.repairs ?? []);
  const showRepairs = live ? active.kind === "prepare" && (active.pass === "repair" || repairs.length > 0) : run?.kind === "prepare" && repairs.length > 0;

  return (
    <ul className="rounded-b-lg">
      {showRepairs && (
        <StepGroup
          title="Repair-safe preparation"
          meta={live && active.currentRepair ? "running" : repairs.length ? `${repairs.filter((r) => r.ok).length}/${repairs.length} done` : "before the kubeconfig checks"}
          worst={repairs.length ? (repairs.some((r) => !r.ok) ? "block" : "pass") : undefined}
          pending={!repairs.length && !(live && active.currentRepair)}
          running={live && active.pass === "repair" && Boolean(active.currentRepair)}
          open={toggled.repairs ?? true}
          onToggle={() => setToggled((t) => ({ ...t, repairs: !(t.repairs ?? true) }))}
        >
          {repairs.map((r) => (
            <RepairRow key={r.name} repair={r} />
          ))}
          {live && active.currentRepair && <RepairRow repair={active.currentRepair} running />}
          {live && active.pass === "repair" && !active.currentRepair && repairs.length === 0 && <li className="py-1.5 pl-10 text-[12.5px] text-fg-3">Repairs run before the kubeconfig checks.</li>}
        </StepGroup>
      )}
      {allGroups.map((g) => {
        const done = live ? g.checks.filter((c) => active.done.includes(c)) : g.checks;
        const runningHere = live && active.current?.group === g.id;
        const pending = live && !runningHere && done.length === 0;
        const complete = !live || done.length === g.checks.length;
        const worst = groupChecks(done)[0]?.worst;
        const defaultOpen = runningHere || (complete && (worst === "warn" || worst === "block"));
        const open = toggled[g.id] ?? defaultOpen;
        return (
          <StepGroup
            key={g.id}
            title={g.label}
            meta={pending ? "" : runningHere ? `${done.length}/${g.checks.length}` : `${g.checks.length} ${g.checks.length === 1 ? "check" : "checks"} · ${ms(done.reduce((s, c) => s + c.ms, 0))}`}
            worst={complete ? worst : undefined}
            running={runningHere}
            pending={pending || (!complete && !runningHere)}
            open={open}
            onToggle={() => setToggled((t) => ({ ...t, [g.id]: !open }))}
          >
            {g.checks.map((c) => (
              <CheckRow key={c.id} check={c} running={live && active.current?.id === c.id} pending={live && !active.done.includes(c) && active.current?.id !== c.id} />
            ))}
          </StepGroup>
        );
      })}
    </ul>
  );
}

function HistoryList({ runs, selected, onSelect }: { runs: ReadinessRun[]; selected?: string; onSelect: (id: string) => void }) {
  return (
    <ol className="grid">
      {runs.map((run, i) => {
        const s = summarize(run.checks);
        return (
          <li key={run.id} className="border-t border-line first:border-t-0">
            <button
              type="button"
              aria-pressed={selected === run.id}
              onClick={() => onSelect(run.id)}
              className={clsx("grid w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 px-4 py-2.5 text-left", selected === run.id ? "bg-accent-soft" : "hover:bg-surface-2")}
            >
              <span className="flex items-center gap-2 text-[13px]">
                <CheckMark level={run.status === "READY" ? "pass" : "block"} />
                <span className={clsx("font-medium", run.status === "BLOCKED" ? "text-warn" : "text-fg")}>{run.status === "READY" ? "Ready" : "Blocked"}</span>
                <span className="text-fg-2">{KIND_WORD[run.kind]}</span>
                {i === 0 && <Tag>Latest</Tag>}
              </span>
              <span className="num text-[11.5px] text-fg-3">{ms(run.finishedAt - run.startedAt)}</span>
              <span className="col-span-2 truncate text-[12px] text-fg-3">
                {stamp(run.finishedAt)} UTC · <span className="ident">{run.mode}</span>
                {s.warn ? ` · ${s.warn} warning` : ""}
                {run.origin !== "history" && " · this session"}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

export default function ChecklistCI() {
  const { fresh, runs, latest, active, now } = useFreshness();
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [scopeOpen, setScopeOpen] = useState(false);
  const selected = active ? undefined : (runs.find((r) => r.id === selectedId) ?? latest);
  const viewing = active ? undefined : selected;
  const s = viewing ? summarize(viewing.checks) : undefined;
  const disk = (viewing?.checks ?? []).find((c) => c.id === "artifacts_disk" && c.level === "warn");
  const needed = viewing ? repairsForRun(viewing.checks) : [];

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex justify-end">
        <ScenarioSwitch />
      </div>

      <section className="grid gap-4 rounded-lg border border-line bg-surface p-4 sm:p-5" aria-label="Lane readiness">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="label">Selected lane · private</div>
            <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h2 className="ident text-[20px] font-medium tracking-[-0.01em]">{LANE.profile}</h2>
              <StatusWord fresh={fresh} className="text-[14px]" />
              {fresh.state === "fresh" && <span className="num text-[13px] text-fg-2">fresh for {countdown(fresh.left)}</span>}
            </div>
            <p className="mt-1 text-[13px] text-fg-3">{freshnessLine(fresh)}</p>
          </div>
          <RunActions />
        </div>
        <FreshnessBar fresh={fresh} />
        <div className="grid gap-4 border-t border-line pt-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <LaneFacts />
          <div className="grid content-start gap-2 text-[12.5px] text-fg-2">
            <p>
              <span className="font-medium text-fg">Run preflight</span> checks only. <span className="font-medium text-fg">Prepare environment</span> may repair this lane's own services, then rechecks.
            </p>
            <button type="button" aria-expanded={scopeOpen} onClick={() => setScopeOpen(!scopeOpen)} className="flex cursor-pointer items-center gap-1 justify-self-start text-fg-3 hover:text-fg">
              <ChevronRight className={clsx("size-3.5 transition-transform", scopeOpen && "rotate-90")} strokeWidth={2} />
              What preparation may change
            </button>
            {scopeOpen && <RepairScope highlight={needed} />}
          </div>
        </div>
      </section>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Checks">
          <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-line px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <h3 className="text-[13.5px] font-medium">
                {active ? `${KIND_WORD[active.kind]} · ${active.pass === "recheck" ? "recheck" : active.kind === "prepare" ? "repair-safe" : "check-only"}` : viewing ? `${KIND_WORD[viewing.kind]} · ${viewing.mode}` : "No preflight yet"}
              </h3>
              <Tag tone="accent">Demo</Tag>
            </div>
            <span className="num text-[12px] text-fg-3">
              {active
                ? `${active.done.length}/${active.total} · ${ms(Math.max(0, now - active.startedAt))}`
                : viewing && s
                  ? `${s.pass} passed${s.warn ? ` · ${s.warn} warning` : ""}${s.block ? ` · ${s.block} blocked` : ""} · ${ms(viewing.finishedAt - viewing.startedAt)} · ${ago(now - viewing.finishedAt)}`
                  : ""}
            </span>
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
          {viewing?.status === "BLOCKED" && needed.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-line px-4 py-2.5 text-[12.5px] text-fg-2">
              <Wrench className="size-3.5 text-fg-3" strokeWidth={1.75} />
              Preparation can address {needed.length} of the failing areas:
              {needed.map((n) => (
                <Tip key={n} content="See What preparation may change.">
                  <span tabIndex={0} className="ident text-fg">
                    {n}
                  </span>
                </Tip>
              ))}
            </div>
          )}
          <RunSteps key={active ? `${active.id}-${active.pass}` : viewing?.id} run={viewing} active={active} />
        </section>

        <aside className="rounded-lg border border-line bg-surface" aria-label="Preflight history">
          <header className="border-b border-line px-4 py-3">
            <h3 className="text-[13.5px] font-medium">History</h3>
            <p className="mt-0.5 text-[12px] text-fg-3">Preflight and preparation jobs on this lane.</p>
          </header>
          <HistoryList runs={runs} selected={viewing?.id} onSelect={setSelectedId} />
        </aside>
      </div>
    </div>
  );
}
