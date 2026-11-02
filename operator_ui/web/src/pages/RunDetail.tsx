import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowLeft } from "lucide-react";
import { useEffect, useMemo } from "react";
import { Link, useLocation, useParams } from "react-router";
import { api } from "@/api/client";
import type { CaseRow } from "@/api/types";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { ErrorState, LoadingState } from "@/components/states";
import { LabLogo } from "@/components/ModelCard";
import { Kpi, Outcome, Panel, Tag, Tip } from "@/components/ui";
import { labOf } from "@/data/models";
import { caseFamily, humanize } from "@/lib/cases";
import { buildConfigs, caseOutcome, techniqueLabel } from "@/lib/explore";
import { compact, count, duration, pct, runDate, usd } from "@/lib/format";
import { KpiStrip } from "./ModelDetail";

const rowCost = (row: CaseRow) => {
  const values = [row.metrics.api?.cost, row.metrics.debug?.cost, row.metrics.verification?.cost].filter((v): v is number => typeof v === "number");
  return values.length ? values.reduce((a, b) => a + b, 0) : null;
};
const rowTokens = (row: CaseRow) => {
  const values = [row.metrics.api?.total_tokens, row.metrics.debug?.total_tokens, row.metrics.verification?.total_tokens].filter((v): v is number => typeof v === "number");
  return values.length ? values.reduce((a, b) => a + b, 0) : null;
};

function Verifier({ row }: { row: CaseRow }) {
  if (row.verified === null || row.ground_truth_passed === null) return <span className="text-fg-3">—</span>;
  const agrees = row.verified === row.ground_truth_passed;
  return (
    <Tip content={`Verifier judged the repair ${row.verified ? "successful" : "unsuccessful"}. Ground Truth ${row.ground_truth_passed ? "passed" : "failed"}.`}>
      <span className={clsx("text-[12.5px]", agrees ? "text-fg-2" : "text-warn")}>{agrees ? "Agrees" : "Disagrees"}</span>
    </Tip>
  );
}

export function RunDetailPage() {
  const { ref = "" } = useParams();
  const { hash } = useLocation();
  const query = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const found = useMemo(() => {
    const run = query.data?.find((r) => r.ref === ref);
    if (!run || !query.data) return undefined;
    const config = buildConfigs(query.data, "all").find((c) => c.runs.some((r) => r.ref === ref));
    return { run, config };
  }, [query.data, ref]);

  const target = decodeURIComponent(hash.slice(1));
  useEffect(() => {
    if (target && found) document.getElementById(`attempt-${target}`)?.scrollIntoView({ block: "center" });
  }, [target, found]);

  if (query.isLoading) return <LoadingState label="Reading run" />;
  if (query.error) return <ErrorState error={query.error} />;
  if (!found) return <ErrorState error={new Error("This run is not in the recorded data.")} />;
  const { run, config } = found;
  const verifierRate = run.verification_comparable ? run.verification_correct / run.verification_comparable : null;

  return (
    <div className="grid gap-8">
      <div>
        <Link to={config ? `/models/${config.slug}` : "/"} className="inline-flex items-center gap-1.5 text-[13px] text-fg-3 hover:text-fg">
          <ArrowLeft className="size-3.5" strokeWidth={1.75} />
          {config ? <span className="ident">{config.debug}</span> : "Models"}
        </Link>
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
          <h1 className="text-[26px] leading-tight font-medium tracking-[-0.02em]">Run {runDate(run.run_id)}</h1>
          <Tag tone={run.status === "incomplete" ? "warn" : "neutral"}>{run.status}</Tag>
          <Tag>{run.source}</Tag>
        </div>
        <p className="mt-2 flex flex-wrap items-center gap-x-2 text-[14px] text-fg-2">
          {config && <LabLogo lab={labOf(config.debug)} size={14} />}
          <span className="ident text-fg">{run.models.DebugAgent.join(", ") || "unrecorded"}</span>
          <span className="text-fg-3">·</span>
          <span>{techniqueLabel(run.technique)}</span>
          <span className="text-fg-3">·</span>
          <span className="ident text-fg-3">{run.run_id}</span>
        </p>
      </div>

      <KpiStrip>
        <Kpi label="Ground Truth" value={pct(run.ground_truth_rate)} detail={`${run.ground_truth_passed} of ${run.ground_truth_known} known`} />
        <Kpi label="Observed" value={`${run.observed_cases}/${run.planned_cases}`} detail={run.ground_truth_unavailable ? `${run.ground_truth_unavailable} unknown outcomes` : "All outcomes known"} />
        <Kpi label="Verifier agrees" value={pct(verifierRate, 0)} detail={`${run.verification_comparable} comparable`} />
        <Kpi label="Duration" value={duration(run.duration_s)} detail="Whole run" />
        <Kpi label="Cost" value={usd(run.total_cost)} detail={`${compact(run.total_tokens)} tokens`} />
      </KpiStrip>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Panel title="Attempts" caption="One attempt per case. Ground Truth is the authoritative outcome; the verifier and the runner status are separate signals." flush>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-[13px]">
              <thead>
                <tr className="label text-left !text-[10.5px] [&>th]:h-9 [&>th]:border-b [&>th]:border-line [&>th]:px-3 [&>th]:font-medium">
                  <th className="!pl-4">Case</th>
                  <th>Ground Truth</th>
                  <th>Verifier</th>
                  <th>Runner</th>
                  <th className="text-right">Time</th>
                  <th className="text-right">Tokens</th>
                  <th className="!pr-4 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {run.case_rows.map((row) => {
                  const { family, variant } = caseFamily(row.case);
                  return (
                    <tr key={row.case} id={`attempt-${row.case}`} className={clsx("border-b border-line last:border-b-0", target === row.case ? "bg-accent-soft" : "hover:bg-surface-2/60")}>
                      <td className="py-2 pr-3 pl-4">
                        <div className="text-[12.5px] text-fg-2">{humanize(family)}</div>
                        <VariantCard id={row.case}>
                          <span tabIndex={0} className={clsx(HINT, "ident text-[12px] text-fg")}>
                            {variant}
                          </span>
                        </VariantCard>
                      </td>
                      <td className="px-3">
                        <Outcome outcome={caseOutcome(row)} />
                      </td>
                      <td className="px-3">
                        <Verifier row={row} />
                      </td>
                      <td className="px-3">
                        <span className="label !text-[10.5px]">{row.status}</span>
                      </td>
                      <td className="num px-3 text-right text-fg-2">{duration(row.duration_s)}</td>
                      <td className="num px-3 text-right text-fg-2">{compact(rowTokens(row))}</td>
                      <td className="num pr-4 pl-3 text-right text-fg-2">{usd(rowCost(row))}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="grid gap-6 xl:sticky xl:top-20 xl:self-start">
          <Panel title="Provenance">
            <dl className="grid gap-3 text-[13px]">
              {[
                ["Source", run.source === "canonical" ? "Canonical export in data/" : run.source === "exploratory" ? "Exploratory pack in data/exploratory" : "Local operator run"],
                ["Run ID", <span className="ident">{run.run_id}</span>],
                ["Reference", <span className="ident break-all">{run.ref}</span>],
                ["Knowledge model", <span className="ident">{run.models.API.join(", ") || "—"}</span>],
                ["Debug model", <span className="ident">{run.models.DebugAgent.join(", ") || "—"}</span>],
                ["Verifier", <span className="ident">{run.models.Verification.join(", ") || "—"}</span>],
                ["Technique", techniqueLabel(run.technique)],
                ["Cases", `${count(run.observed_cases)} observed of ${count(run.planned_cases)} planned`],
              ].map(([label, value]) => (
                <div key={String(label)} className="grid grid-cols-[112px_minmax(0,1fr)] gap-3">
                  <dt className="text-fg-3">{label}</dt>
                  <dd className="text-fg">{value}</dd>
                </div>
              ))}
            </dl>
          </Panel>
          <p className="px-1 text-[12px] leading-relaxed text-fg-3">
            Values come straight from the run's recorded summaries. Missing outcomes stay unknown; nothing is inferred or backfilled.
          </p>
        </div>
      </div>
    </div>
  );
}
