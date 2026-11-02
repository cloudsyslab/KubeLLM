import clsx from "clsx";
import { ChevronRight, SquareTerminal, Wrench } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Tag } from "@/components/ui";
import { CheckMark, KIND_WORD, groupChecks, isRepairable, ms, stamp, summarize, type ActiveRun, type ReadinessCheck, type ReadinessRun, type RepairResult } from "./readiness";

// The run as CI steps: check_readiness.py's groups in run order, each check a
// row that opens its terminal output. Preparation's repairs come first.

export type Selected = { kind: "check"; id: string } | { kind: "repair"; name: string };

export const pickKey = (pick: Selected) => (pick.kind === "check" ? `check-${pick.id}` : `repair-${pick.name}`);
export const samePick = (a?: Selected, b?: Selected) => Boolean(a && b && pickKey(a) === pickKey(b));
/** The DOM id of a step row, for scrolling to it. */
export const rowIdOf = (pick: Selected) => `readiness-${pickKey(pick)}`;

function Row({
  rowId,
  selected,
  running,
  pending,
  focused,
  onSelect,
  mark,
  title,
  detail,
  meta,
  inline,
}: {
  rowId: string;
  selected: boolean;
  running?: boolean;
  pending?: boolean;
  focused?: boolean;
  onSelect: () => void;
  mark: ReactNode;
  title: ReactNode;
  detail?: ReactNode;
  meta: ReactNode;
  inline?: ReactNode;
}) {
  return (
    <li id={rowId} className="scroll-mt-[72px]">
      <button
        type="button"
        aria-pressed={selected}
        disabled={pending}
        onClick={onSelect}
        className={clsx(
          "relative grid w-full grid-cols-[16px_minmax(0,1fr)_auto] items-baseline gap-x-3 py-1.5 pr-4 pl-10 text-left text-[12.5px] transition-colors",
          pending ? "cursor-default" : "cursor-pointer",
          selected ? "bg-accent-soft" : running ? "bg-accent-soft/50" : !pending && "hover:bg-surface-2",
        )}
      >
        {focused && <span aria-hidden className="absolute inset-y-1.5 left-[26px] w-[2px] rounded-full bg-accent" />}
        <span className="translate-y-[2px]">{mark}</span>
        <span className="min-w-0">
          {title}
          {detail}
        </span>
        <span className="num inline-flex items-center gap-1.5 text-[11.5px] text-fg-3">
          {selected && <SquareTerminal aria-hidden className="size-3 text-accent" strokeWidth={1.75} />}
          {meta}
        </span>
      </button>
      {inline}
    </li>
  );
}

function CheckRow({ check, running, pending, ...rest }: { check: ReadinessCheck; running?: boolean; pending?: boolean; rowId: string; selected: boolean; focused: boolean; onSelect: () => void; inline?: ReactNode }) {
  const mono = check.group === "live" || check.group === "static";
  return (
    <Row
      {...rest}
      running={running}
      pending={pending}
      mark={<CheckMark level={check.level} running={running} pending={pending} />}
      title={<span className={clsx(mono ? "ident" : "", pending ? "text-fg-3" : "text-fg")}>{check.label}</span>}
      detail={
        !pending &&
        !running && (
          <span className={clsx("mt-0.5 block leading-snug", check.level === "pass" ? "text-fg-3" : "text-fg-2")}>
            {check.detail}
            {check.level !== "pass" && isRepairable(check) && (
              <span className="ml-2 inline-flex items-center gap-1 text-fg-3">
                <Wrench className="size-3" strokeWidth={1.75} /> preparation may repair
              </span>
            )}
          </span>
        )
      }
      meta={pending ? "" : running ? "…" : ms(check.ms)}
    />
  );
}

function RepairRow({ repair, running, ...rest }: { repair: RepairResult; running?: boolean; rowId: string; selected: boolean; onSelect: () => void; inline?: ReactNode }) {
  return (
    <Row
      {...rest}
      running={running}
      mark={running ? <CheckMark running /> : <CheckMark level={repair.ok ? "pass" : "block"} />}
      title={
        <>
          <span className="text-fg">{repair.label}</span> <span className="ident text-[11px] text-fg-3">{repair.name}</span>
        </>
      }
      detail={!running && <span className={clsx("mt-0.5 block leading-snug", repair.ok ? "text-fg-3" : "text-warn")}>{repair.message}</span>}
      meta={running ? "…" : ms(repair.ms)}
    />
  );
}

function StepGroup({ title, meta, worst, running, pending, focused, open, onToggle, children }: { title: string; meta: string; worst?: ReadinessCheck["level"]; running?: boolean; pending?: boolean; focused?: boolean; open: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <li className="border-t border-line first:border-t-0">
      <button type="button" aria-expanded={open} onClick={onToggle} className="grid w-full cursor-pointer grid-cols-[14px_16px_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2 text-left hover:bg-surface-2">
        <ChevronRight className={clsx("size-3.5 text-fg-3 transition-transform", open && "rotate-90")} strokeWidth={2} />
        <CheckMark level={worst} running={running} pending={pending} />
        <span className="flex min-w-0 items-center gap-2">
          <span className={clsx("truncate text-[13px]", pending ? "text-fg-3" : "text-fg")}>{title}</span>
          {focused && !open && <span aria-label="Has checks of the selected dependency" className="size-1.5 shrink-0 rounded-full bg-accent" />}
        </span>
        <span className="num text-[11.5px] text-fg-3">{meta}</span>
      </button>
      {open && <ul className="pb-1.5">{children}</ul>}
    </li>
  );
}

/**
 * Every group of the run (or the streaming run) in order. Groups with a
 * problem, the running group, and the group of the selected check open by
 * themselves. `inline` renders the selected row's terminal under it on narrow
 * screens.
 */
export function RunSteps({
  run,
  active,
  selected,
  onSelect,
  focus,
  inline,
}: {
  run?: ReadinessRun;
  active?: ActiveRun;
  selected?: Selected;
  onSelect: (pick: Selected) => void;
  focus: Set<string>;
  inline?: (pick: Selected) => ReactNode;
}) {
  const [toggled, setToggled] = useState<Record<string, boolean>>({});
  const live = active !== undefined;
  const allGroups = groupChecks(live ? active.target : (run?.checks ?? []));
  const repairs = live ? active.repairs : (run?.repairs ?? []);
  const showRepairs = live ? active.kind === "prepare" && (active.pass === "repair" || repairs.length > 0) : run?.kind === "prepare" && repairs.length > 0;
  const selectedGroup = selected?.kind === "check" ? allGroups.find((g) => g.checks.some((c) => c.id === selected.id))?.id : selected ? "repairs" : undefined;

  // Selecting a check (here or from a card) opens its group again.
  useEffect(() => {
    if (!selectedGroup) return;
    setToggled((t) => {
      if (!(selectedGroup in t)) return t;
      const next = { ...t };
      delete next[selectedGroup];
      return next;
    });
  }, [selectedGroup, selected]);

  const pickOf = (pick: Selected) => ({ rowId: rowIdOf(pick), selected: samePick(selected, pick), onSelect: () => onSelect(pick), inline: samePick(selected, pick) ? inline?.(pick) : undefined });

  return (
    <ul>
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
            <RepairRow key={r.name} repair={r} {...pickOf({ kind: "repair", name: r.name })} />
          ))}
          {live && active.currentRepair && <RepairRow repair={active.currentRepair} running {...pickOf({ kind: "repair", name: active.currentRepair.name })} />}
          {live && active.pass === "repair" && !active.currentRepair && repairs.length === 0 && <li className="py-1.5 pl-10 text-[12.5px] text-fg-3">Repairs run before the kubeconfig checks.</li>}
        </StepGroup>
      )}
      {allGroups.map((g) => {
        const done = live ? g.checks.filter((c) => active.done.includes(c)) : g.checks;
        const runningHere = live && active.current?.group === g.id;
        const pending = live && !runningHere && done.length === 0;
        const complete = !live || done.length === g.checks.length;
        const worst = groupChecks(done)[0]?.worst;
        const defaultOpen = runningHere || (complete && (worst === "warn" || worst === "block")) || selectedGroup === g.id;
        const open = toggled[g.id] ?? defaultOpen;
        return (
          <StepGroup
            key={g.id}
            title={g.label}
            meta={pending ? "" : runningHere ? `${done.length}/${g.checks.length}` : `${g.checks.length} ${g.checks.length === 1 ? "check" : "checks"} · ${ms(done.reduce((s, c) => s + c.ms, 0))}`}
            worst={complete ? worst : undefined}
            running={runningHere}
            pending={pending || (!complete && !runningHere)}
            focused={g.checks.some((c) => focus.has(c.id))}
            open={open}
            onToggle={() => setToggled((t) => ({ ...t, [g.id]: !open }))}
          >
            {g.checks.map((c) => (
              <CheckRow
                key={c.id}
                check={c}
                running={live && active.current?.id === c.id}
                pending={live && !active.done.includes(c) && active.current?.id !== c.id}
                focused={focus.has(c.id)}
                {...pickOf({ kind: "check", id: c.id })}
              />
            ))}
          </StepGroup>
        );
      })}
    </ul>
  );
}

export function HistoryList({ runs, selected, onSelect }: { runs: ReadinessRun[]; selected?: string; onSelect: (id: string) => void }) {
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
              <span className="flex min-w-0 items-center gap-2 text-[13px]">
                <CheckMark level={run.status === "READY" ? "pass" : "block"} />
                <span className={clsx("font-medium", run.status === "BLOCKED" ? "text-warn" : "text-fg")}>{run.status === "READY" ? "Ready" : "Blocked"}</span>
                <span className="truncate text-fg-2">{KIND_WORD[run.kind]}</span>
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
