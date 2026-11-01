import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { api } from "@/api/client";
import type { RunWithCases } from "@/api/types";
import { Dot, Kpi, Outcome, Panel, Tag, Tip } from "@/components/ui";
import { ErrorState, LoadingState } from "@/components/states";
import { groupCases, humanize } from "@/lib/cases";
import { caseOutcome, findConfig, techniqueLabel, type ModelConfig } from "@/lib/explore";
import { compact, count, duration, pct, runDate, usd } from "@/lib/format";

export function KpiStrip({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3 lg:grid-cols-5 [&>*]:bg-surface [&>*]:px-4 [&>*]:py-3.5">{children}</div>;
}

function RateBar({ rate }: { rate: number | null }) {
  return (
    <span className="relative inline-block h-1.5 w-20 overflow-hidden rounded-full bg-track align-middle">
      {rate !== null && <span className="absolute inset-y-0 left-0 rounded-full bg-fg-2" style={{ width: `${rate * 100}%` }} />}
    </span>
  );
}

function RunsTable({ config }: { config: ModelConfig }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] text-[13px]">
        <thead>
          <tr className="label text-left !text-[10.5px] [&>th]:h-9 [&>th]:border-b [&>th]:border-line [&>th]:px-3 [&>th]:font-medium">
            <th className="!pl-4">Run</th>
            <th>Ground Truth</th>
            <th className="text-right">Known / attempts</th>
            <th className="text-right">Verifier agrees</th>
            <th className="text-right">Duration</th>
            <th className="text-right">Cost</th>
            <th>Status</th>
            <th className="w-8" />
          </tr>
        </thead>
        <tbody>
          {config.runs.map((run) => (
            <tr key={run.ref} className="group border-b border-line last:border-b-0 hover:bg-surface-2/60">
              <td className="py-2.5 pr-3 pl-4">
                <Link to={`/runs/${run.ref}`} className="block">
                  <div className="text-fg">{runDate(run.run_id)}</div>
                  <div className="ident mt-0.5 text-[11.5px] text-fg-3">{run.run_id}</div>
                </Link>
              </td>
              <td className="px-3">
                <span className="inline-flex items-center gap-2.5">
                  <RateBar rate={run.ground_truth_rate} />
                  <span className="num font-medium">{pct(run.ground_truth_rate)}</span>
                </span>
              </td>
              <td className="num px-3 text-right text-fg-2">
                {run.ground_truth_known} <span className="text-fg-3">/ {run.observed_cases}</span>
              </td>
              <td className="num px-3 text-right text-fg-2">{pct(run.verification_comparable ? run.verification_correct / run.verification_comparable : null, 0)}</td>
              <td className="num px-3 text-right text-fg-2">{duration(run.duration_s)}</td>
              <td className="num px-3 text-right text-fg-2">{usd(run.total_cost)}</td>
              <td className="px-3">
                {run.status === "incomplete" ? (
                  <Tip content={`${run.ground_truth_unavailable} attempt(s) lack a Ground Truth outcome${run.observed_cases < run.planned_cases ? `; ${run.planned_cases - run.observed_cases} planned case(s) missing` : ""}. Nothing is inferred.`}>
                    <span>
                      <Tag tone="warn">Incomplete</Tag>
                    </span>
                  </Tip>
                ) : (
                  <Tag>Recorded</Tag>
                )}
              </td>
              <td className="pr-3 text-right">
                <Link to={`/runs/${run.ref}`} aria-label={`Open run ${run.run_id}`} className="inline-grid size-6 place-items-center text-fg-3 group-hover:text-fg">
                  <ChevronRight className="size-4" strokeWidth={1.75} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OutcomeCell({ outcome, run, id }: { outcome: "pass" | "fail" | "unknown" | null; run: RunWithCases; id: string }) {
  const label = outcome === null ? "Not attempted" : outcome === "pass" ? "Passed Ground Truth" : outcome === "fail" ? "Failed Ground Truth" : "Outcome unknown";
  return (
    <Tip content={<div><div className="ident text-fg">{id}</div><div>{runDate(run.run_id)}: {label}</div></div>}>
      <Link
        to={`/runs/${run.ref}#${id}`}
        aria-label={`${id}, ${runDate(run.run_id)}: ${label}`}
        className={clsx(
          "block size-[18px] rounded-[3px] transition-transform hover:scale-110",
          outcome === "pass" && "bg-good",
          outcome === "fail" && "border border-bad/70 bg-bad-soft",
          outcome === "unknown" && "hatch border border-line-strong",
          outcome === null && "border border-dashed border-line",
        )}
      />
    </Tip>
  );
}

function CaseRuns({ config, focusCase }: { config: ModelConfig; focusCase: string | null }) {
  const families = groupCases(config.cases);
  const runs = [...config.runs].sort((a, b) => a.run_id.localeCompare(b.run_id));
  const outcome = (run: RunWithCases, id: string) => {
    const row = run.case_rows.find((r) => r.case === id);
    return row ? caseOutcome(row) : null;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-[13px]">
        <thead>
          <tr className="label text-left !text-[10.5px] [&>th]:h-9 [&>th]:border-b [&>th]:border-line [&>th]:font-medium">
            <th className="pl-4">Case</th>
            {runs.map((run, index) => (
              <th key={run.ref} className="w-8 text-center">
                <Tip content={`${runDate(run.run_id)} · ${run.run_id}`}>
                  <span>R{index + 1}</span>
                </Tip>
              </th>
            ))}
            <th className="pr-3 pl-4 text-right">Passed</th>
            <th className="pr-4 text-right">Median time</th>
          </tr>
        </thead>
        {families.map((family) => (
          <tbody key={family.family} className="border-b border-line last:border-b-0">
            {family.cases.map((item, index) => {
              const tally = config.perCase.get(item.id);
              const sorted = [...(tally?.durations ?? [])].sort((a, b) => a - b);
              return (
                <tr key={item.id} id={`case-${item.id}`} className={clsx("transition-colors", focusCase === item.id ? "bg-accent-soft" : "hover:bg-surface-2/60")}>
                  <td className="py-1.5 pr-3 pl-4">
                    <div className="flex items-baseline gap-2">
                      <span className={clsx("w-48 shrink-0 truncate text-[12.5px]", index === 0 ? "text-fg-2" : "text-transparent")} aria-hidden={index !== 0} title={humanize(family.family)}>
                        {humanize(family.family)}
                      </span>
                      <span className="ident truncate text-[12px] text-fg">{item.variant}</span>
                    </div>
                  </td>
                  {runs.map((run) => (
                    <td key={run.ref} className="py-1.5">
                      <span className="grid place-items-center">
                        <OutcomeCell outcome={outcome(run, item.id)} run={run} id={item.id} />
                      </span>
                    </td>
                  ))}
                  <td className="num pr-3 pl-4 text-right">
                    <span className={clsx(tally && tally.known > 0 && tally.passed === 0 ? "text-bad" : "text-fg")}>{tally?.passed ?? 0}</span>
                    <span className="text-fg-3">/{tally?.known ?? 0}</span>
                  </td>
                  <td className="num pr-4 text-right text-fg-2">{duration(sorted.length ? sorted[Math.floor(sorted.length / 2)] : null)}</td>
                </tr>
              );
            })}
          </tbody>
        ))}
      </table>
    </div>
  );
}

const ROLES = [
  { key: "api", label: "Knowledge", hint: "Knowledge (API) agent" },
  { key: "debug", label: "Debug", hint: "Debug agent under test" },
  { key: "verification", label: "Verification", hint: "Independent verifier" },
] as const;

function RoleBreakdown({ config }: { config: ModelConfig }) {
  const totals = ROLES.map((role) => {
    let tokens = 0;
    let cost = 0;
    let seconds = 0;
    let costed = 0;
    let rows = 0;
    for (const run of config.runs) {
      for (const row of run.case_rows) {
        const metrics = row.metrics[role.key];
        if (!metrics) continue;
        rows += 1;
        tokens += metrics.total_tokens ?? 0;
        seconds += metrics.duration_s ?? 0;
        if (typeof metrics.cost === "number") {
          cost += metrics.cost;
          costed += 1;
        }
      }
    }
    return { ...role, tokens: rows ? tokens / rows : null, cost: costed ? cost / costed : null, seconds: rows ? seconds / rows : null };
  });
  const totalSeconds = totals.reduce((sum, t) => sum + (t.seconds ?? 0), 0);
  const shades = ["var(--fg-3)", "var(--accent)", "var(--fg-2)"];

  return (
    <div className="grid gap-4">
      <div>
        <div className="flex h-2.5 overflow-hidden rounded-full bg-track">
          {totals.map((t, i) => (
            <span key={t.key} style={{ width: `${totalSeconds ? ((t.seconds ?? 0) / totalSeconds) * 100 : 0}%`, background: shades[i] }} />
          ))}
        </div>
        <div className="mt-1.5 text-[12px] text-fg-3">Share of agent time per attempt</div>
      </div>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="label text-left !text-[10.5px] [&>th]:pb-2 [&>th]:font-medium">
            <th>Role</th>
            <th className="text-right">Time</th>
            <th className="text-right">Tokens</th>
            <th className="text-right">Cost</th>
          </tr>
        </thead>
        <tbody>
          {totals.map((t, i) => (
            <tr key={t.key} className="border-t border-line">
              <td className="py-2">
                <Tip content={t.hint}>
                  <span className="inline-flex items-center gap-2">
                    <span className="size-2 rounded-[2px]" style={{ background: shades[i] }} />
                    {t.label}
                  </span>
                </Tip>
              </td>
              <td className="num text-right text-fg-2">{duration(t.seconds)}</td>
              <td className="num text-right text-fg-2">{compact(t.tokens)}</td>
              <td className="num text-right text-fg-2">{usd(t.cost)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[12px] text-fg-3">Averages per attempt from recorded case metrics. A dash means the role recorded no value.</p>
    </div>
  );
}

export function ModelDetailPage() {
  const { slug = "" } = useParams();
  const [params] = useSearchParams();
  const focusCase = params.get("case");
  const query = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const config = useMemo(() => (query.data ? findConfig(query.data, slug) : undefined), [query.data, slug]);

  useEffect(() => {
    if (focusCase && config) document.getElementById(`case-${focusCase}`)?.scrollIntoView({ block: "center" });
  }, [focusCase, config]);

  if (query.isLoading) return <LoadingState label="Reading model runs" />;
  if (query.error) return <ErrorState error={query.error} />;
  if (!config) return <ErrorState error={new Error("This model configuration is not in the recorded runs.")} />;

  const rates = config.runRates.filter((r) => r.rate !== null).map((r) => r.rate as number);
  const backScope = config.source === "canonical" ? "/" : `/?scope=${config.source}`;

  return (
    <div className="grid gap-8">
      <div>
        <Link to={backScope} className="inline-flex items-center gap-1.5 text-[13px] text-fg-3 hover:text-fg">
          <ArrowLeft className="size-3.5" strokeWidth={1.75} />
          Models
        </Link>
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
          <Dot color={config.color} className="size-2.5" />
          <h1 className="ident text-[26px] leading-tight font-medium tracking-[-0.02em]">{config.debug}</h1>
          <Tag>{techniqueLabel(config.technique)}</Tag>
          <Tag tone={config.source === "canonical" ? "neutral" : "warn"}>{config.source}</Tag>
        </div>
        <p className="mt-2 text-[14px] text-fg-2">
          Knowledge model <span className="ident text-fg">{config.api}</span> · verifier <span className="ident text-fg">{config.verification}</span> · {config.cases.length} cases × {config.runs.length} {config.runs.length === 1 ? "run" : "runs"}
        </p>
      </div>

      <KpiStrip>
        <Kpi label="Ground Truth" value={pct(config.rate)} detail={`${count(config.passed)} of ${count(config.known)} known`} />
        <Kpi label="Run spread" value={rates.length ? (rates.length > 1 ? `${pct(Math.min(...rates), 0)}–${pct(Math.max(...rates), 0)}` : pct(rates[0], 0)) : "—"} detail={`${rates.length} ${rates.length === 1 ? "run" : "runs"} with outcomes`} />
        <Kpi label="Verifier agrees" value={pct(config.verifyAgree, 0)} detail={`${count(config.verifyComparable)} comparable attempts`} />
        <Kpi label="Time / attempt" value={duration(config.medianAttemptS)} detail="Median, all phases" />
        <Kpi label="Cost / attempt" value={usd(config.costPerAttempt)} detail={`${config.costRuns} of ${config.runs.length} runs recorded cost`} />
      </KpiStrip>

      {config.unknown > 0 && (
        <div className="flex items-start gap-3 rounded-lg border border-warn/30 bg-warn-soft px-4 py-3 text-[13px]">
          <Tag tone="warn">Unknown</Tag>
          <p className="text-fg-2">
            {config.unknown} of {config.attempts} attempts have no recorded Ground Truth outcome. They are excluded from the success rate and never counted as passes or failures.
          </p>
        </div>
      )}

      <Panel title="Runs" caption="Each run attempted every case once. Open a run for its attempts, metrics, and provenance." flush>
        <RunsTable config={config} />
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Panel
          title="Cases across runs"
          caption="One square per attempt. Select a square to open that attempt in its run."
          actions={
            <div className="flex items-center gap-3 text-[12px] text-fg-3">
              <Outcome outcome="pass" compact />
              <Outcome outcome="fail" compact />
              <Outcome outcome="unknown" compact />
            </div>
          }
          flush
        >
          <CaseRuns config={config} focusCase={focusCase} />
        </Panel>
        <div className="xl:sticky xl:top-20 xl:self-start">
          <Panel title="Where an attempt spends" caption="By agent role">
            <RoleBreakdown config={config} />
          </Panel>
        </div>
      </div>
    </div>
  );
}
