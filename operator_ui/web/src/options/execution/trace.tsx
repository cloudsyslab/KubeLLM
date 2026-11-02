import clsx from "clsx";
import { Search } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Segmented } from "@/components/ui";
import type { DemoAttempt, DemoEvent, DemoPhase, PhaseKey } from "@/demo/campaign";
import { duration } from "@/lib/format";
import { LogLine, phaseLook, phaseStatus } from "./shared";

export type OutputScope = "phase" | "attempt" | "campaign";

// The attempt's phases on one time axis. Bars use the grid's colors: the live
// phase in the accent, Ground Truth in the attempt's outcome, a runner error
// in amber; dashed outlines are each phase's recorded length.
export function Waterfall({
  attempt,
  t,
  errorPhase,
  selected,
  onSelect,
}: {
  attempt: DemoAttempt;
  t: number;
  errorPhase?: PhaseKey;
  selected: PhaseKey;
  onSelect: (phase: PhaseKey) => void;
}) {
  const span = Math.max(1, attempt.end - attempt.start);
  return (
    <div>
      <div className="grid gap-0.5" role="group" aria-label="Phases">
        {attempt.phases.map((p) => {
          const status = phaseStatus(attempt, p.key, t, errorPhase);
          const reached = t >= p.start;
          const left = ((p.start - attempt.start) / span) * 100;
          const planned = ((p.end - p.start) / span) * 100;
          const width = Math.max(0.8, ((Math.min(t, p.end) - p.start) / span) * 100);
          const look = phaseLook(status);
          return (
            <button
              key={p.key}
              type="button"
              disabled={!reached}
              aria-pressed={p.key === selected}
              aria-label={`${p.label}: ${look.word}${reached ? `, ${duration(Math.min(t, p.end) - p.start)}` : ""}`}
              onClick={() => onSelect(p.key)}
              className={clsx(
                "grid cursor-pointer grid-cols-[88px_minmax(0,1fr)_52px] items-center gap-3 rounded-[4px] px-1.5 py-1 text-left disabled:cursor-default",
                p.key === selected ? "bg-surface-2" : "hover:bg-surface-2/60",
              )}
            >
              <span className={clsx("truncate text-[12.5px]", reached ? "text-fg" : "text-fg-3")}>{p.label}</span>
              <span className="relative h-3.5">
                <span className="absolute inset-y-0 rounded-[2px] border border-dashed border-line-strong" style={{ left: `${left}%`, width: `${planned}%` }} />
                {reached && <span className={clsx("absolute inset-y-0 rounded-[2px]", look.className)} style={{ left: `${left}%`, width: `${width}%` }} />}
              </span>
              <span className="num text-right text-[12px] text-fg-3">{reached ? duration(Math.min(t, p.end) - p.start) : "—"}</span>
            </button>
          );
        })}
      </div>
      <p className="mt-1.5 px-1.5 text-[11.5px] text-fg-3">Dashed outlines show each phase's recorded length in the replayed run.</p>
    </div>
  );
}

// One output stream for the attempt: the selected phase, the whole attempt,
// or the whole campaign. While following the live attempt it sticks to the
// newest line.
export function TraceOutput({
  events,
  attempt,
  phase,
  scope,
  onScope,
  query,
  onQuery,
  live,
  t,
}: {
  events: DemoEvent[];
  attempt: DemoAttempt;
  phase: DemoPhase;
  scope: OutputScope;
  onScope: (scope: OutputScope) => void;
  query: string;
  onQuery: (query: string) => void;
  live: boolean;
  t: number;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const lines = useMemo(() => {
    const pool = events.filter((e) => scope === "campaign" || (e.attempt === attempt.index && (scope === "attempt" || e.phase === phase.key)));
    const q = query.trim().toLowerCase();
    return q ? pool.filter((e) => e.text.toLowerCase().includes(q)) : pool;
  }, [events, scope, attempt.index, phase.key, query]);
  const newest = events[events.length - 1];
  const streaming = live && newest?.attempt === attempt.index;

  // A new view starts at the newest line when it is live, at the top otherwise.
  useLayoutEffect(() => {
    const el = scroller.current;
    if (!el) return;
    stick.current = streaming;
    el.scrollTop = streaming ? el.scrollHeight : 0;
  }, [scope, attempt.index, phase.key]);

  useEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [lines.length]);

  return (
    <div className="min-w-0 rounded-md border border-line">
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-2.5 py-2">
        <Segmented
          label="Output scope"
          value={scope}
          onChange={onScope}
          options={[
            { value: "phase", label: phase.label, hint: "The selected phase" },
            { value: "attempt", label: "Attempt", hint: "Every phase of this attempt" },
            { value: "campaign", label: "Campaign", hint: "Every attempt so far" },
          ]}
        />
        <label className="flex h-8 min-w-[140px] flex-1 items-center gap-2 rounded-md bg-surface-2 px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent">
          <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
          <input value={query} onChange={(e) => onQuery(e.target.value)} placeholder="Search output" aria-label="Search output" className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-3 py-1.5 text-[12px] text-fg-3">
        {scope === "phase" && (
          <>
            <span className="num">{duration(Math.max(0, Math.min(t, phase.end) - phase.start))}</span>
            {phase.tokens ? <span className="num">{phase.tokens.toLocaleString()} tokens</span> : null}
          </>
        )}
        <span className="num">
          {lines.length} {lines.length === 1 ? "line" : "lines"}
          {query ? " match" : ""}
        </span>
        <span className="ml-auto">Credentials redacted</span>
      </div>
      <div
        ref={scroller}
        role="log"
        aria-label="Output"
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
        }}
        className="h-[300px] overflow-y-auto px-3 py-2"
      >
        {lines.length ? (
          lines.map((event, i) => <LogLine key={`${event.t}-${i}`} event={event} showAttempt={scope === "campaign"} dense live={streaming && event === newest && i === lines.length - 1} />)
        ) : (
          <p className="py-10 text-center text-[12.5px] text-fg-3">{query ? "No lines match." : "No output for this phase yet."}</p>
        )}
      </div>
    </div>
  );
}
