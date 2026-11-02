import clsx from "clsx";
import { CircleAlert } from "lucide-react";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { Tip } from "@/components/ui";
import { DEMO_CASES, DEMO_MODELS, type CampaignView, type DemoCampaign } from "@/demo/campaign";
import { useReplay } from "@/demo/replay";
import { caseFamily, humanize } from "@/lib/cases";
import { attemptLook, ModelLabel, phaseOf } from "./shared";

export function FailureCallout({ campaign, view }: { campaign: DemoCampaign; view: CampaignView }) {
  if (view.status !== "failed") return null;
  const failed = campaign.attempts[campaign.attempts.length - 1];
  const error = campaign.events.find((e) => e.level === "error");
  return (
    <div className="flex items-start gap-3 rounded-lg border border-warn/35 bg-warn-soft px-4 py-3" role="alert">
      <CircleAlert className="mt-0.5 size-4 shrink-0 text-warn" strokeWidth={2} />
      <div className="grid gap-1 text-[13px]">
        <div className="font-medium text-fg">Campaign stopped on a runner error in attempt {failed.index + 1}</div>
        <p className="text-fg-2">{error?.text}</p>
        <p className="text-fg-3">
          Teardown completed for that attempt. {view.planned - campaign.attempts.length} planned attempts were not started. This is a runner error, not a Ground Truth failure; it does not count against the model.
        </p>
      </div>
    </div>
  );
}

// Every planned attempt, models down and cases across, filling in live.
export function AttemptGrid({ view, selected, onSelect }: { view: CampaignView; selected: number; onSelect: (index: number) => void }) {
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
                        disabled={!attempt || t < attempt.start}
                        aria-pressed={selected === index}
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

export function GridLegend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-fg-3">
      {(["pass", "fail", "unknown", "running", "pending", "error"] as const).map((state) => (
        <span key={state} className="inline-flex items-center gap-1.5">
          <span className={clsx("size-2.5 rounded-[2px]", attemptLook(state).className, "motion-safe:animate-none")} />
          {attemptLook(state).word}
        </span>
      ))}
    </div>
  );
}
