import clsx from "clsx";
import { ArrowDownToLine, Search } from "lucide-react";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Tip } from "@/components/ui";
import type { DemoEvent, Source } from "@/demo/campaign";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { StageFallback } from "../OptionsRoom";
import { FailureCallout } from "./GridFirst";
import { JobHeader, ModelLabel } from "./shared";

const BUCKETS = 72;
const SOURCES: (Source | "all")[] = ["all", "runner", "kubectl", "knowledge", "debug", "verifier", "truth"];
const PHASE_LABEL: Record<DemoEvent["phase"], string> = { setup: "setup", knowledge: "knowledge", debug: "debug", verify: "verify", truth: "truth", teardown: "teardown" };

const isProblem = (e: DemoEvent) => e.level === "error" || e.level === "warn" || e.level === "fail";

function Histogram({ events, total, t, onPick }: { events: DemoEvent[]; total: number; t: number; onPick: (time: number) => void }) {
  const buckets = useMemo(() => {
    const out = Array.from({ length: BUCKETS }, () => ({ normal: 0, problem: 0 }));
    for (const e of events) {
      const b = Math.min(BUCKETS - 1, Math.floor((e.t / total) * BUCKETS));
      if (isProblem(e)) out[b].problem += 1;
      else out[b].normal += 1;
    }
    return out;
  }, [events, total]);
  const max = Math.max(4, ...buckets.map((b) => b.normal + b.problem));
  const now = (t / total) * 100;

  return (
    <div>
      <div className="relative flex h-16 items-end gap-[2px]" role="img" aria-label="Output volume over the campaign">
        {buckets.map((b, i) => {
          const start = (i / BUCKETS) * total;
          const future = start > t;
          return (
            <Tip key={i} content={`${clock(start)}–${clock(start + total / BUCKETS)} · ${b.normal + b.problem} lines${b.problem ? ` · ${b.problem} warnings or failures` : ""}`}>
              <button type="button" onClick={() => onPick(start)} disabled={future} aria-label={`Jump to ${clock(start)}`} className="flex h-full flex-1 cursor-pointer flex-col justify-end disabled:cursor-default">
                {future ? (
                  <span className="h-px w-full bg-line" />
                ) : (
                  <>
                    {b.problem > 0 && <span className="w-full rounded-t-[1px] bg-bad/80" style={{ height: `${(b.problem / max) * 100}%` }} />}
                    <span className={clsx("w-full bg-fg-3/70 hover:bg-fg-2", b.problem ? "" : "rounded-t-[1px]")} style={{ height: `${(b.normal / max) * 100}%` }} />
                  </>
                )}
              </button>
            </Tip>
          );
        })}
        <span className="pointer-events-none absolute inset-y-0 w-px bg-accent" style={{ left: `${now}%` }} aria-hidden />
      </div>
      <div className="num mt-1.5 flex justify-between text-[11px] text-fg-3">
        <span>0:00</span>
        <span>{clock(total / 2)}</span>
        <span>{clock(total)}</span>
      </div>
    </div>
  );
}

export default function ConsoleFirst() {
  const { campaign, view, t } = useReplay();
  const [source, setSource] = useState<Source | "all">("all");
  const [problemsOnly, setProblemsOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [follow, setFollow] = useState(true);
  const [anchor, setAnchor] = useState<number | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  const events = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (view?.events ?? []).filter((e) => (source === "all" || e.source === source) && (!problemsOnly || isProblem(e)) && (!q || e.text.toLowerCase().includes(q)));
  }, [view?.events, source, problemsOnly, query]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    if (anchor !== null) {
      el.querySelector<HTMLElement>(`[data-t="${anchor}"]`)?.scrollIntoView({ block: "start" });
    } else if (follow) el.scrollTop = el.scrollHeight;
  }, [events.length, follow, anchor]);

  if (!campaign || !view) return <StageFallback />;

  const pick = (time: number) => {
    const first = events.find((e) => e.t >= time);
    setFollow(false);
    setAnchor(first ? first.t : null);
  };

  return (
    <div className="grid gap-4">
      <FailureCallout campaign={campaign} view={view} />
      <section className="overflow-hidden rounded-lg border border-line bg-surface">
        <div className="grid gap-4 border-b border-line p-4">
          <JobHeader compact />
          <Histogram events={view.events} total={campaign.total} t={t} onPick={pick} />
        </div>

        <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2">
          <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Source">
            {SOURCES.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={source === value}
                onClick={() => setSource(value)}
                className={clsx("h-7 cursor-pointer rounded-md border px-2.5 font-mono text-[11.5px]", source === value ? "border-line-strong bg-surface-3 text-fg" : "border-transparent text-fg-3 hover:text-fg")}
              >
                {value}
              </button>
            ))}
          </div>
          <button
            type="button"
            aria-pressed={problemsOnly}
            onClick={() => setProblemsOnly(!problemsOnly)}
            className={clsx("h-7 cursor-pointer rounded-md border px-2.5 text-[12px]", problemsOnly ? "border-bad/40 bg-bad-soft text-bad" : "border-line text-fg-3 hover:text-fg")}
          >
            Warnings and failures
          </button>
          <label className="ml-auto flex h-7 w-full items-center gap-2 rounded-md bg-surface-2 px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent sm:w-64">
            <Search className="size-3.5" strokeWidth={1.75} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search output" aria-label="Search output" className="w-full bg-transparent text-fg outline-none placeholder:text-fg-3" />
          </label>
          <button
            type="button"
            aria-pressed={follow}
            onClick={() => {
              setFollow(!follow);
              setAnchor(null);
            }}
            className={clsx("inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border px-2.5 text-[12px]", follow ? "border-accent-line bg-accent-soft text-accent" : "border-line text-fg-3 hover:text-fg")}
          >
            <ArrowDownToLine className="size-3.5" strokeWidth={1.75} /> Follow
          </button>
        </div>

        <div className="overflow-x-auto">
          <div className="min-w-[720px]">
            <div className="grid grid-cols-[56px_40px_76px_76px_minmax(0,1fr)] gap-3 border-b border-line px-4 py-1.5 font-mono text-[10.5px] tracking-[0.06em] text-fg-3 uppercase">
              <span>Time</span>
              <span>#</span>
              <span>Phase</span>
              <span>Source</span>
              <span>Message</span>
            </div>
            <div ref={scroller} className="h-[480px] overflow-y-auto px-4 py-1" onWheel={() => follow && setFollow(false)} aria-live="polite">
              {events.map((event, i) => {
                const prev = events[i - 1];
                const attempt = campaign.attempts[event.attempt];
                const tone = { info: "text-fg-2", command: "text-fg", output: "text-fg-3", warn: "text-warn", error: "text-bad", pass: "text-good", fail: "text-bad" }[event.level];
                return (
                  <Fragment key={`${event.t}-${i}`}>
                    {(!prev || prev.attempt !== event.attempt) && (
                      <div className="mt-2 mb-1 flex items-center gap-2 border-t border-line pt-2 text-[12px] text-fg-2 first:mt-0 first:border-t-0">
                        <span className="font-mono text-fg-3">#{event.attempt + 1}</span>
                        <ModelLabel model={attempt.model} />
                        <span className="text-fg-3">·</span>
                        <span>{humanize(attempt.caseId)}</span>
                      </div>
                    )}
                    <div data-t={event.t} className={clsx("grid grid-cols-[56px_40px_76px_76px_minmax(0,1fr)] items-baseline gap-3 rounded-sm py-[1px] font-mono text-[11.5px] leading-[1.55] hover:bg-surface-2", anchor === event.t && "bg-accent-soft")}>
                      <span className="num text-fg-3">{clock(event.t)}</span>
                      <span className="num text-fg-3">{event.attempt + 1}</span>
                      <span className="text-fg-3">{PHASE_LABEL[event.phase]}</span>
                      <span className="text-fg-3">{event.source}</span>
                      <span className={clsx("break-words", tone)}>
                        {event.level === "command" && <span className="text-fg-3 select-none">$ </span>}
                        {event.text}
                      </span>
                    </div>
                  </Fragment>
                );
              })}
              {!events.length && <p className="py-10 text-center text-[12.5px] text-fg-3">No output matches these filters.</p>}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-line px-4 py-2 text-[12px] text-fg-3">
          <span>
            {events.length} of {view.events.length} lines · credentials redacted
          </span>
          <span>History survives refresh and reconnect (persisted event IDs)</span>
        </div>
      </section>
    </div>
  );
}
