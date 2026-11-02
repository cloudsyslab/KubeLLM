import clsx from "clsx";
import type { ReactNode } from "react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Outcome } from "@/components/ui";
import { PHASES, type DemoAttempt, type DemoEvent, type PhaseKey } from "@/demo/campaign";
import { clock } from "@/demo/ReplayBar";
import { duration } from "@/lib/format";
import { PhaseMark, phaseStatus } from "./shared";

export function storyOf(events: DemoEvent[]) {
  const symptom = events.find((e) => e.text.startsWith("fixture ready"))?.text.replace(/^fixture ready · symptom: /, "");
  const plan = events.find((e) => e.source === "knowledge" && e.text.startsWith("plan drafted"))?.text.replace(/^plan drafted: /, "");
  const commands = events
    .filter((e) => e.source === "debug" && e.level === "command")
    .map((e) => e.text.replace(/^kubectl --context \S+ /, "").split(" ").slice(0, 2).join(" "));
  const verifier = events.find((e) => e.text.startsWith("verifier judgment"))?.text.replace(/^verifier judgment: /, "");
  const checks = events.filter((e) => e.source === "truth");
  const error = events.find((e) => e.level === "error");
  const teardown = events.find((e) => e.text.startsWith("teardown verified"));
  return { symptom, plan, commands, verifier, checks, error, teardown };
}

// What each phase contributes to the story of an attempt.
const STORY_LABEL: Record<PhaseKey, string> = {
  setup: "Symptom",
  knowledge: "Plan",
  debug: "Agent ran",
  verify: "Verifier",
  truth: "Ground Truth",
  teardown: "Teardown",
};

function Now({ event }: { event?: DemoEvent }) {
  return (
    <span className="flex min-w-0 items-baseline gap-2 font-mono text-[12px] text-fg-2">
      <span aria-hidden className="size-1.5 shrink-0 translate-y-[-1px] rounded-full bg-accent motion-safe:animate-pulse" />
      <span className="line-clamp-2 break-words">{event?.text ?? "Starting"}</span>
    </span>
  );
}

// The attempt as a story: symptom, plan, what the agent ran, the verifier's
// view, and the Ground Truth verdict, one row per phase. Each row's label
// selects that phase in the trace.
export function AttemptStory({
  attempt,
  events,
  t,
  errorPhase,
  selected,
  onSelect,
}: {
  attempt: DemoAttempt;
  events: DemoEvent[];
  t: number;
  errorPhase?: PhaseKey;
  selected: PhaseKey;
  onSelect: (phase: PhaseKey) => void;
}) {
  const story = storyOf(events);
  const verdicts = story.checks.filter((c) => c.level === "pass" || c.level === "fail");
  const passedChecks = verdicts.filter((c) => c.level === "pass").length;

  return (
    <ol>
      {PHASES.map((meta) => {
        const phase = attempt.phases.find((p) => p.key === meta.key);
        const status = phaseStatus(attempt, meta.key, t, errorPhase);
        const reached = status !== "pending" && status !== "skipped";
        const live = status === "current";
        const latest = [...events].reverse().find((e) => e.phase === meta.key);
        const elapsed = phase && reached ? duration(Math.min(t, phase.end) - phase.start) : status === "skipped" ? "skipped" : "—";

        let content: ReactNode = <span className="text-fg-3">—</span>;
        if (status === "skipped") content = <span className="text-fg-3">{errorPhase ? "Skipped after the runner error." : "Not run for this attempt."}</span>;
        else if (reached) {
          switch (meta.key) {
            case "setup":
              content = story.error ? (
                <span className="text-warn">{story.error.text}</span>
              ) : story.symptom ? (
                <VariantCard id={attempt.caseId}>
                  <span tabIndex={0} className={clsx(HINT, "text-fg")}>
                    {story.symptom}
                  </span>
                </VariantCard>
              ) : (
                <Now event={latest} />
              );
              break;
            case "knowledge":
              content = story.plan ?? <Now event={latest} />;
              break;
            case "debug":
              content = story.commands.length ? (
                <span className="flex flex-wrap gap-1.5">
                  {story.commands.map((command, i) => {
                    const newest = live && i === story.commands.length - 1;
                    return (
                      <span key={i} className={clsx("rounded-[4px] border px-1.5 py-0.5 font-mono text-[11.5px]", newest ? "border-accent-line bg-accent-soft text-fg" : "border-transparent bg-surface-2 text-fg")}>
                        kubectl {command}
                      </span>
                    );
                  })}
                </span>
              ) : (
                <Now event={latest} />
              );
              break;
            case "verify":
              content = story.verifier ? (
                <span>
                  {story.verifier === "not recorded" ? "No judgment recorded." : `Judged it ${story.verifier}.`} <span className="text-fg-3">A separate signal from Ground Truth.</span>
                </span>
              ) : (
                <Now event={latest} />
              );
              break;
            case "truth":
              content =
                status === "pass" || status === "fail" || status === "unknown" ? (
                  <span className="grid gap-1">
                    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <Outcome outcome={status} compact />
                      {status !== "unknown" && verdicts.length > 0 && (
                        <span className="num text-fg-2">
                          {passedChecks} of {verdicts.length} checks passed
                        </span>
                      )}
                    </span>
                    {status === "fail" &&
                      story.checks
                        .filter((c) => c.level === "fail" && c.text.startsWith("✗"))
                        .map((c, i) => (
                          <span key={i} className="text-bad">
                            {c.text}
                          </span>
                        ))}
                    {status === "unknown" && <span className="text-fg-3">The recorded run has no deterministic verdict for this case; it is counted as unknown, not as a failure.</span>}
                  </span>
                ) : (
                  <Now event={latest} />
                );
              break;
            case "teardown":
              content = story.teardown ? `Lane restored to its baseline at ${clock(story.teardown.t)}.` : <Now event={latest} />;
              break;
          }
        }

        const on = selected === meta.key && reached;
        return (
          <li key={meta.key} className={clsx("grid gap-x-4 gap-y-1.5 border-b border-line px-4 py-2.5 last:border-b-0 sm:grid-cols-[152px_minmax(0,1fr)]", on && "bg-surface-2/70")}>
            <button
              type="button"
              disabled={!reached}
              aria-pressed={on}
              onClick={() => onSelect(meta.key)}
              title={reached ? `Show the ${meta.label} phase in the trace` : undefined}
              className="group flex cursor-pointer items-start gap-2.5 rounded-[4px] text-left disabled:cursor-default"
            >
              <span className="pt-[5px]">
                <PhaseMark status={status} />
              </span>
              <span className="grid min-w-0">
                <span className={clsx("text-[13px]", reached ? "text-fg group-hover:underline group-hover:decoration-line-strong group-hover:underline-offset-4" : "text-fg-3")}>{STORY_LABEL[meta.key]}</span>
                <span className="num truncate font-mono text-[11px] text-fg-3">
                  {STORY_LABEL[meta.key] === meta.label ? elapsed : `${meta.label.toLowerCase()} · ${elapsed}`}
                </span>
              </span>
            </button>
            <div className={clsx("min-w-0 text-[13px] leading-relaxed", reached ? "text-fg-2" : "text-fg-3")}>{content}</div>
          </li>
        );
      })}
    </ol>
  );
}
