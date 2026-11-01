import clsx from "clsx";
import { ArrowRight, ChevronRight, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Tag } from "@/components/ui";
import {
  CheckMark,
  FreshnessBar,
  GROUPS,
  KIND_WORD,
  LANE,
  LEVEL_WORD,
  LiveAnnouncer,
  RepairScope,
  RunActions,
  ScenarioSwitch,
  StatusWord,
  countdown,
  freshnessLine,
  ms,
  stamp,
  useFreshness,
  type ActiveRun,
  type ReadinessRun,
} from "./readiness";

const dayOf = (epoch: number) => new Date(epoch).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });

function runMark(run: ReadinessRun) {
  return run.status === "BLOCKED" ? ("block" as const) : ("pass" as const);
}

function LiveNode({ active, now }: { active: ActiveRun; now: number }) {
  const group = GROUPS.find((g) => g.id === active.current?.group);
  return (
    <li className="relative grid grid-cols-[20px_minmax(0,1fr)] gap-x-3 pb-4">
      <span className="relative z-[1] mt-0.5 grid size-5 place-items-center rounded-full border border-accent bg-accent-soft">
        <CheckMark running className="size-3" />
      </span>
      <div className="min-w-0 rounded-md border border-accent-line bg-accent-soft/60 px-3 py-2">
        <div className="flex items-center justify-between gap-2 text-[13px]">
          <span className="font-medium text-fg">{KIND_WORD[active.kind]} running</span>
          <span className="num text-[11.5px] text-fg-3">{ms(Math.max(0, now - active.startedAt))}</span>
        </div>
        <div className="mt-0.5 text-[12px] text-fg-2">
          {active.currentRepair ? `Repairing: ${active.currentRepair.label}` : group ? `${group.label} · ${active.current?.label}` : active.label}
        </div>
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-3">
          <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${(active.done.length / active.total) * 100}%` }} />
        </div>
        <div className="num mt-1 text-[11px] text-fg-3">
          {active.pass === "recheck" ? "Recheck · " : active.pass === "repair" ? "Repair-safe pass · " : ""}
          {active.done.length}/{active.total} checks
        </div>
      </div>
    </li>
  );
}

function Timeline({ runs, active, now, base, compare, onBase, onCompare }: { runs: ReadinessRun[]; active?: ActiveRun; now: number; base?: string; compare?: string; onBase: (id: string) => void; onCompare: (id: string) => void }) {
  let lastDay = "";
  return (
    <ol className="relative grid" aria-label="Preflight and preparation history">
      <span aria-hidden className="absolute top-2 bottom-2 left-[9.5px] w-px bg-line-strong" />
      {active && <LiveNode active={active} now={now} />}
      {runs.map((run) => {
        const day = dayOf(run.finishedAt);
        const header = day !== lastDay;
        lastDay = day;
        const mark = runMark(run);
        const isBase = base === run.id;
        const isCompare = compare === run.id;
        return (
          <li key={run.id} className="relative">
            {header && <div className="label relative z-[1] mb-2 ml-8 !text-[10px]">{day}</div>}
            <div className="grid grid-cols-[20px_minmax(0,1fr)] gap-x-3 pb-3">
              <span className={clsx("relative z-[1] mt-1 grid size-5 place-items-center rounded-full border bg-surface", mark === "pass" ? "border-line-strong" : "border-warn/50")}>
                <CheckMark level={mark} className="size-3" />
              </span>
              <div className={clsx("min-w-0 rounded-md border px-3 py-2", isCompare ? "border-accent-line bg-accent-soft" : isBase ? "border-line-strong bg-surface-2" : "border-transparent")}>
                <button type="button" onClick={() => onCompare(run.id)} aria-pressed={isCompare} className="grid w-full cursor-pointer gap-0.5 text-left">
                  <span className="flex items-center gap-2 text-[13px]">
                    <span className={clsx("font-medium", run.status === "BLOCKED" ? "text-warn" : "text-fg")}>{run.status === "READY" ? "Ready" : "Blocked"}</span>
                    <span className="text-fg-2">{KIND_WORD[run.kind]}</span>
                    <span className="num ml-auto text-[11.5px] text-fg-3">{new Date(run.finishedAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })}</span>
                  </span>
                  <span className="truncate text-[12px] text-fg-3">{run.summary}</span>
                </button>
                <div className="mt-1.5 flex items-center gap-2 text-[11.5px]">
                  {isCompare && <Tag tone="accent">After</Tag>}
                  {isBase && <Tag>Before</Tag>}
                  {!isBase && !isCompare && (
                    <button type="button" onClick={() => onBase(run.id)} className="cursor-pointer text-fg-3 hover:text-fg">
                      Set as before
                    </button>
                  )}
                  {run.origin !== "history" && <span className="text-fg-3">{run.origin === "session" ? "This session" : "Demo state"}</span>}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function RunPicker({ id, label, runs, value, onChange }: { id: string; label: string; runs: ReadinessRun[]; value?: string; onChange: (id: string) => void }) {
  return (
    <label htmlFor={id} className="grid min-w-0 gap-1 text-[12px] text-fg-3">
      {label}
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 min-w-0 cursor-pointer rounded-md border border-line-strong bg-surface px-2 text-[12.5px] text-fg outline-none focus-visible:outline-2 focus-visible:outline-accent"
      >
        {runs.map((run) => (
          <option key={run.id} value={run.id}>
            {run.status === "READY" ? "Ready" : "Blocked"} · {KIND_WORD[run.kind]} · {stamp(run.finishedAt)}
          </option>
        ))}
      </select>
    </label>
  );
}

function Diff({ before, after, between }: { before: ReadinessRun; after: ReadinessRun; between: ReadinessRun[] }) {
  const [showSame, setShowSame] = useState(false);
  const pairs = after.checks.map((check) => ({ after: check, before: before.checks.find((c) => c.id === check.id) }));
  const changed = pairs.filter((p) => p.before?.level !== p.after.level || p.before?.detail !== p.after.detail);
  const same = pairs.filter((p) => !changed.includes(p));
  const reversed = before.finishedAt > after.finishedAt;
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px]">
        <span className="inline-flex items-center gap-1.5">
          <CheckMark level={runMark(before)} />
          <span className={before.status === "BLOCKED" ? "text-warn" : "text-fg"}>{before.status === "READY" ? "Ready" : "Blocked"}</span>
          <span className="text-fg-3">{stamp(before.finishedAt)}</span>
        </span>
        <ArrowRight className="size-3.5 text-fg-3" strokeWidth={1.75} aria-label="to" />
        <span className="inline-flex items-center gap-1.5">
          <CheckMark level={runMark(after)} />
          <span className={after.status === "BLOCKED" ? "text-warn" : "text-fg"}>{after.status === "READY" ? "Ready" : "Blocked"}</span>
          <span className="text-fg-3">{stamp(after.finishedAt)}</span>
        </span>
        <span className="num ml-auto text-[12px] text-fg-3">
          {changed.length} changed · {same.length} unchanged · {ms(before.finishedAt - before.startedAt)} → {ms(after.finishedAt - after.startedAt)}
        </span>
      </div>
      {reversed && <p className="text-[12px] text-fg-3">“Before” is newer than “after”; the diff reads backwards in time.</p>}

      {between.length > 0 && (
        <div className="rounded-md border border-line px-3 py-2.5">
          <div className="label mb-1.5 !text-[10px]">In between</div>
          <ul className="grid gap-2">
            {between.map((run) => (
              <li key={run.id} className="grid gap-1 text-[12.5px]">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-fg">{KIND_WORD[run.kind]}</span>
                  <span className="ident text-[11.5px] text-fg-3">{run.mode}</span>
                  <span className="text-fg-3">{stamp(run.finishedAt)}</span>
                </span>
                {run.repairs.map((r) => (
                  <span key={r.name} className="flex items-start gap-2 pl-1 text-fg-2">
                    <Wrench className="mt-[3px] size-3 shrink-0 text-fg-3" strokeWidth={1.75} />
                    <span>
                      {r.label}: <span className={r.ok ? "text-fg-2" : "text-warn"}>{r.message}</span>
                    </span>
                  </span>
                ))}
                {!run.repairs.length && <span className="text-fg-3">{run.summary}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {changed.length ? (
        <ul className="@container grid" aria-label="Changed checks">
          {changed.map(({ before: b, after: a }) => (
            <li key={a.id} className="grid gap-2 border-t border-line py-2.5 text-[12.5px]">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className={clsx(a.group === "live" || a.group === "static" ? "ident" : "", "text-fg")}>{a.label}</span>
                <span className="text-[11.5px] text-fg-3">{GROUPS.find((g) => g.id === a.group)?.label}</span>
              </div>
              <div className="grid gap-2 @lg:grid-cols-2">
                <div className="rounded-md border border-line px-2.5 py-2">
                  <div className="label mb-1 !text-[10px]">Before</div>
                  {b ? (
                    <>
                      <span className="inline-flex items-center gap-1.5">
                        <CheckMark level={b.level} />
                        <span className={b.level === "pass" ? "text-fg-2" : "text-warn"}>{LEVEL_WORD[b.level]}</span>
                      </span>
                      <span className="mt-0.5 block leading-snug text-fg-3">{b.detail}</span>
                    </>
                  ) : (
                    <span className="text-fg-3">Not checked</span>
                  )}
                </div>
                <div className="rounded-md border border-accent-line bg-accent-soft/40 px-2.5 py-2">
                  <div className="label mb-1 !text-[10px]">After</div>
                  <span className="inline-flex items-center gap-1.5">
                    <CheckMark level={a.level} />
                    <span className={a.level === "pass" ? "text-fg" : "text-warn"}>{LEVEL_WORD[a.level]}</span>
                  </span>
                  <span className="mt-0.5 block leading-snug text-fg-2">{a.detail}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-md border border-dashed border-line-strong px-3 py-4 text-center text-[12.5px] text-fg-3">No check changed between these runs.</p>
      )}

      <div>
        <button type="button" aria-expanded={showSame} onClick={() => setShowSame(!showSame)} className="flex cursor-pointer items-center gap-1 text-[12.5px] text-fg-3 hover:text-fg">
          <ChevronRight className={clsx("size-3.5 transition-transform", showSame && "rotate-90")} strokeWidth={2} />
          {same.length} unchanged checks
        </button>
        {showSame && (
          <ul className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
            {same.map(({ after: a }) => (
              <li key={a.id} className="flex min-w-0 items-center gap-2 text-[12.5px]">
                <CheckMark level={a.level} />
                <span className={clsx("truncate text-fg-2", (a.group === "live" || a.group === "static") && "ident")}>{a.label}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function RunTimeline() {
  const { fresh, runs, active, now } = useFreshness();
  const [base, setBase] = useState<string | undefined>("f61b4e9d08a5");
  const [compare, setCompare] = useState<string | undefined>("5d2e8a0c7f13");
  const [scope, setScope] = useState(false);
  const newest = runs[0]?.id;
  const seen = useRef(newest);

  // A run that finishes in this session becomes "after", compared with the one before it.
  useEffect(() => {
    if (newest && newest !== seen.current) {
      seen.current = newest;
      setCompare(newest);
      setBase(runs[1]?.id);
    }
  }, [newest, runs]);

  const before = runs.find((r) => r.id === base) ?? runs[1];
  const after = runs.find((r) => r.id === compare) ?? runs[0];
  const [lo, hi] = before && after ? [Math.min(before.finishedAt, after.finishedAt), Math.max(before.finishedAt, after.finishedAt)] : [0, 0];
  const between = runs.filter((r) => r.finishedAt > lo && r.finishedAt < hi).reverse();

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <section className="grid gap-3 rounded-lg border border-line bg-surface p-4" aria-label="Lane readiness">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="ident text-[15px] font-medium">{LANE.profile}</span>
            <StatusWord fresh={fresh} />
            {fresh.state === "fresh" && <span className="num text-[12.5px] text-fg-2">{countdown(fresh.left)} left</span>}
            <span className="text-[12.5px] text-fg-3">{freshnessLine(fresh)}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ScenarioSwitch />
            <RunActions size="sm" />
          </div>
        </div>
        <FreshnessBar fresh={fresh} />
        <button type="button" aria-expanded={scope} onClick={() => setScope(!scope)} className="flex cursor-pointer items-center gap-1 justify-self-start text-[12.5px] text-fg-3 hover:text-fg">
          <ChevronRight className={clsx("size-3.5 transition-transform", scope && "rotate-90")} strokeWidth={2} />
          What preparation may change
        </button>
        {scope && <RepairScope />}
      </section>

      <div className="grid items-start gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <section className="rounded-lg border border-line bg-surface p-4" aria-label="Timeline">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-[13.5px] font-medium">Timeline</h3>
            <Tag tone="accent">Demo</Tag>
          </div>
          <Timeline runs={runs} active={active} now={now} base={before?.id} compare={after?.id} onBase={setBase} onCompare={setCompare} />
        </section>
        <section className="min-w-0 rounded-lg border border-line bg-surface p-4" aria-label="What changed">
          <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <RunPicker id="diff-before" label="Before" runs={runs} value={before?.id} onChange={setBase} />
            <RunPicker id="diff-after" label="After" runs={runs} value={after?.id} onChange={setCompare} />
          </div>
          {before && after ? <Diff before={before} after={after} between={between} /> : <p className="text-[12.5px] text-fg-3">Two runs are needed to compare.</p>}
        </section>
      </div>
    </div>
  );
}

