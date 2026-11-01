import clsx from "clsx";
import { CircleAlert, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Panel, Tip } from "@/components/ui";
import { DEMO_CASES, DEMO_MODELS, type DemoCampaign, type CampaignView } from "@/demo/campaign";
import { useReplay } from "@/demo/replay";
import { caseFamily, humanize } from "@/lib/cases";
import { runDate } from "@/lib/format";
import { StageFallback } from "../OptionsRoom";
import { attemptLook, JobHeader, LogLine, ModelLabel, PhaseSteps, phaseOf } from "./shared";

export function FailureCallout({ campaign, view }: { campaign: DemoCampaign; view: CampaignView }) {
  if (view.status !== "failed") return null;
  const failed = campaign.attempts[campaign.attempts.length - 1];
  const error = campaign.events.find((e) => e.level === "error");
  return (
    <div className="flex items-start gap-3 rounded-lg border border-warn/35 bg-warn-soft px-4 py-3" role="alert">
      <CircleAlert className="mt-0.5 size-4 shrink-0 text-warn" strokeWidth={2} />
      <div className="grid gap-1 text-[13px]">
        <div className="font-medium text-fg">
          Campaign stopped on a runner error in attempt {failed.index + 1}
        </div>
        <p className="text-fg-2">{error?.text}</p>
        <p className="text-fg-3">
          Teardown completed for that attempt. {view.planned - campaign.attempts.length} planned attempts were not started. This is a runner error, not a Ground Truth failure; it does not count against the model.
        </p>
      </div>
    </div>
  );
}

function AttemptGrid({ view, selected, onSelect }: { view: CampaignView; selected: number; onSelect: (index: number) => void }) {
  const { campaign, t } = useReplay();
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] table-fixed border-separate border-spacing-[3px] text-[12px]">
        <thead>
          <tr>
            <th className="w-[150px]" />
            {DEMO_CASES.map((caseId) => {
              const { family, variant } = caseFamily(caseId);
              return (
                <th key={caseId} scope="col" className="px-1 pb-1.5 text-left align-bottom font-normal">
                  <VariantCard id={caseId} side="bottom">
                    <span tabIndex={0} className={clsx(HINT, "block truncate text-[11.5px] text-fg-2")}>
                      {humanize(family)}
                    </span>
                  </VariantCard>
                  <span className="ident block truncate text-[11px] text-fg-3">{variant}</span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {DEMO_MODELS.map((model, row) => (
            <tr key={model}>
              <th scope="row" className="pr-2 text-left text-[12.5px] font-normal">
                <ModelLabel model={model} className="max-w-full text-fg" />
              </th>
              {DEMO_CASES.map((caseId, col) => {
                const index = row * DEMO_CASES.length + col;
                const state = view.states[index];
                const look = attemptLook(state);
                const attempt = campaign?.attempts[index];
                const phase = state === "running" ? phaseOf(attempt, t) : undefined;
                return (
                  <td key={caseId}>
                    <Tip content={`Attempt ${index + 1} · ${humanize(caseId)} · ${phase ? `${phase.label} phase` : look.word}`}>
                      <button
                        type="button"
                        onClick={() => onSelect(index)}
                        disabled={!attempt}
                        aria-label={`Attempt ${index + 1}, ${model}, ${caseId}: ${look.word}`}
                        className={clsx(
                          "flex h-10 w-full cursor-pointer items-center justify-center rounded-[4px] text-[11.5px] transition-shadow disabled:cursor-default",
                          look.className,
                          selected === index && "ring-2 ring-fg ring-offset-1 ring-offset-surface",
                          state === "pass" && "font-medium text-bg",
                          state === "fail" && "text-bad",
                          state === "error" && "text-warn",
                          state === "running" && "font-medium text-accent motion-safe:animate-none",
                          state === "pending" && "text-fg-3",
                        )}
                      >
                        {state === "running" ? phase?.label ?? "Starting" : state === "pending" ? index + 1 : look.word}
                      </button>
                    </Tip>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OutputTail({ focusIndex }: { focusIndex: number }) {
  const { view } = useReplay();
  const [scope, setScope] = useState<"attempt" | "all">("attempt");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const events = useMemo(() => {
    const pool = (view?.events ?? []).filter((e) => scope === "all" || e.attempt === focusIndex);
    const q = query.trim().toLowerCase();
    return q ? pool.filter((e) => e.text.toLowerCase().includes(q)) : pool;
  }, [view?.events, scope, focusIndex, query]);
  const shown = expanded ? events : events.slice(-14);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [shown.length]);

  return (
    <Panel
      title="Output"
      caption={`${events.length} lines${query ? " match" : ""} · credentials redacted`}
      actions={
        <div className="flex items-center gap-1 rounded-md border border-line p-0.5 text-[12px]" role="group" aria-label="Output scope">
          {(["attempt", "all"] as const).map((value) => (
            <button key={value} type="button" aria-pressed={scope === value} onClick={() => setScope(value)} className={clsx("h-6 cursor-pointer rounded-[4px] px-2", scope === value ? "bg-surface-3 text-fg" : "text-fg-3 hover:text-fg")}>
              {value === "attempt" ? "This attempt" : "Campaign"}
            </button>
          ))}
        </div>
      }
      flush
    >
      <div className="border-b border-line px-3 py-2">
        <label className="flex h-7 items-center gap-2 rounded-md bg-surface-2 px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent">
          <Search className="size-3.5" strokeWidth={1.75} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search output" aria-label="Search output" className="w-full bg-transparent text-fg outline-none placeholder:text-fg-3" />
        </label>
      </div>
      <div ref={scroller} className={clsx("overflow-y-auto px-4 py-2.5", expanded ? "h-[420px]" : "max-h-[340px]")} aria-live="polite">
        {shown.length ? shown.map((event, i) => <LogLine key={`${event.t}-${i}`} event={event} showAttempt={scope === "all"} dense />) : <p className="py-6 text-center text-[12.5px] text-fg-3">No output yet.</p>}
      </div>
      {events.length > 14 && (
        <button type="button" onClick={() => setExpanded(!expanded)} className="w-full cursor-pointer border-t border-line px-4 py-2 text-left text-[12.5px] text-fg-3 hover:text-fg">
          {expanded ? "Show the last 14 lines" : `Show all ${events.length} lines`}
        </button>
      )}
    </Panel>
  );
}

export default function GridFirst() {
  const { campaign, view, t } = useReplay();
  const [pinned, setPinned] = useState<number | null>(null);
  if (!campaign || !view) return <StageFallback />;

  const latest = view.current?.index ?? Math.max(0, view.done - 1);
  const focusIndex = pinned !== null && campaign.attempts[pinned] ? pinned : latest;
  const focus = campaign.attempts[focusIndex];
  const focusState = view.states[focusIndex];
  const command = [...view.events].reverse().find((e) => e.attempt === focusIndex && e.level === "command");
  const checks = view.events.filter((e) => e.attempt === focusIndex && e.source === "truth");

  return (
    <div className="grid gap-4">
      <FailureCallout campaign={campaign} view={view} />
      <div className="rounded-lg border border-line bg-surface p-4">
        <JobHeader />
        <div className="mt-4">
          <AttemptGrid view={view} selected={focusIndex} onSelect={(index) => setPinned(index === latest && view.status === "running" ? null : index)} />
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-fg-3">
          {(["pass", "fail", "running", "pending", "error"] as const).map((state) => (
            <span key={state} className="inline-flex items-center gap-1.5">
              <span className={clsx("size-2.5 rounded-[2px]", attemptLook(state).className, "motion-safe:animate-none")} />
              {attemptLook(state).word}
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <Panel
          title={
            <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span>Attempt {focusIndex + 1}</span>
              <span className="text-fg-3">·</span>
              <ModelLabel model={focus.model} className="font-normal" />
              <span className="text-fg-3">·</span>
              <VariantCard id={focus.caseId}>
                <span tabIndex={0} className={clsx(HINT, "font-normal text-fg-2")}>
                  {humanize(focus.caseId)}
                </span>
              </VariantCard>
            </span>
          }
          caption={pinned !== null && focusIndex !== latest ? "Pinned. The campaign keeps running." : view.status === "running" ? "Following the live attempt" : "Last attempt"}
          actions={
            pinned !== null && focusIndex !== latest ? (
              <button type="button" onClick={() => setPinned(null)} className="h-7 cursor-pointer rounded-md border border-line-strong px-2.5 text-[12px] text-fg-2 hover:bg-surface-2 hover:text-fg">
                Back to live
              </button>
            ) : null
          }
        >
          <div className="grid gap-4">
            <PhaseSteps attempt={focus} t={t} />
            {focusState === "running" && command && (
              <div>
                <div className="label mb-1.5 !text-[10px]">Current command</div>
                <div className="rounded-md bg-surface-2 px-3 py-2 font-mono text-[12px] text-fg">
                  <span className="text-fg-3 select-none">$ </span>
                  {command.text}
                </div>
              </div>
            )}
            {checks.length > 0 && (
              <div>
                <div className="label mb-1.5 !text-[10px]">Ground Truth checks</div>
                <ul className="grid gap-1 text-[12.5px]">
                  {checks.map((check, i) => (
                    <li key={i} className={clsx(check.level === "fail" ? "text-bad" : check.level === "pass" ? "text-fg" : "text-fg-2")}>
                      {check.text}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[12px] text-fg-3">
              Outcome and timings replay the recorded run of {runDate(focus.sourceRunId)}. Ground Truth decides the result; the verifier is a separate signal.
            </p>
          </div>
        </Panel>
        <OutputTail focusIndex={focusIndex} />
      </div>
    </div>
  );
}
