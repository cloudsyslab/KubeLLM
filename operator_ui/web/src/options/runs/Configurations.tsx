import clsx from "clsx";
import { ArrowRight, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import type { RunSource } from "@/api/types";
import { VariantCard } from "@/components/CaseCard";
import { HINT } from "@/components/CaseMatrix";
import { ErrorState, LoadingState } from "@/components/states";
import { Button, Segmented, Tag, Tip } from "@/components/ui";
import { caseFamily, groupCases, humanize } from "@/lib/cases";
import { techniqueLabel, type ModelConfig } from "@/lib/explore";
import { count, duration, pct, runDate, usd } from "@/lib/format";
import { MAX_COMPARE, stateOf, type CaseState } from "../compare/model";
import {
  CompareTray,
  compareHref,
  gtTip,
  IncompleteTag,
  matchesQuery,
  RateBar,
  RunModel,
  SearchField,
  SelectBox,
  SOURCE_LABEL,
  useRunSelection,
  useRunViews,
  type RunSelection,
  type RunView,
} from "./shared";

type SortKey = "rate" | "latest" | "runs";

const latestId = (config: ModelConfig) => config.runs[0]?.run_id ?? "";

function spreadOf(config: ModelConfig) {
  const rates = config.runRates.map((r) => r.rate).filter((r): r is number => r !== null);
  if (!rates.length) return null;
  return { min: Math.min(...rates), max: Math.max(...rates), n: rates.length };
}

// One bar per run, oldest first: height is the run's Ground Truth success.
function RunStrip({ views, selection }: { views: RunView[]; selection: RunSelection }) {
  return (
    <div className="flex flex-wrap items-end gap-[3px]" role="group" aria-label="Runs, oldest first">
      {views.map((view) => {
        const { run } = view;
        const on = selection.has(view.ref);
        const rate = run.ground_truth_rate;
        return (
          <Tip
            key={view.ref}
            content={
              <div className="grid gap-0.5">
                <div className="text-fg">{runDate(run.run_id)}</div>
                <div>{gtTip(run)}</div>
                {run.status === "incomplete" && <div className="text-warn">Incomplete run</div>}
                <div className="text-fg-3">{on ? "Selected. Click to remove." : "Click to select for comparison."}</div>
              </div>
            }
          >
            <button
              type="button"
              aria-pressed={on}
              disabled={!on && selection.full}
              onClick={() => selection.toggle(view.ref)}
              aria-label={`Run ${runDate(run.run_id)}: Ground Truth ${pct(rate)}`}
              className={clsx(
                "relative h-8 w-3 shrink-0 cursor-pointer overflow-hidden rounded-[2px] bg-track transition-shadow hover:ring-1 hover:ring-fg-3 disabled:cursor-not-allowed",
                on && "ring-1 ring-accent",
              )}
            >
              {rate === null ? (
                <span className="hatch absolute inset-0" />
              ) : (
                <span className={clsx("absolute inset-x-0 bottom-0", on ? "bg-accent" : "bg-fg-3")} style={{ height: `${Math.max(rate * 100, 4)}%` }} />
              )}
              {run.status === "incomplete" && <span aria-hidden className="absolute inset-x-0 top-0 h-[2px] bg-warn" />}
            </button>
          </Tip>
        );
      })}
    </div>
  );
}

function CaseSquares({ view, families }: { view: RunView; families: { family: string; cases: { id: string }[] }[] }) {
  const tally = { pass: 0, fail: 0, unknown: 0, absent: 0 } as Record<CaseState, number>;
  for (const family of families) for (const item of family.cases) tally[stateOf(view.run, item.id)] += 1;
  return (
    <span
      className="inline-flex items-center gap-[5px]"
      role="img"
      aria-label={`${tally.pass} passed, ${tally.fail} failed, ${tally.unknown} unknown${tally.absent ? `, ${tally.absent} not recorded` : ""}`}
    >
      {families.map((family) => (
        <span key={family.family} className="inline-flex gap-[2px]">
          {family.cases.map((item) => {
            const state = stateOf(view.run, item.id);
            return (
              <span
                key={item.id}
                title={`${item.id}: ${state === "pass" ? "passed" : state === "fail" ? "failed" : state === "unknown" ? "outcome unknown" : "not recorded"}`}
                className={clsx(
                  "size-2 rounded-[1.5px]",
                  state === "pass" && "bg-good",
                  state === "fail" && "border border-bad/70 bg-bad-soft",
                  state === "unknown" && "hatch border border-line-strong",
                  state === "absent" && "border border-dashed border-line-strong",
                )}
              />
            );
          })}
        </span>
      ))}
    </span>
  );
}

function CaseList({ ids, tone }: { ids: string[]; tone: "bad" | "neutral" }) {
  return (
    <span className="inline-flex flex-wrap gap-1.5">
      {ids.map((id) => {
        const { family, variant } = caseFamily(id);
        return (
          <VariantCard key={id} id={id} side="top">
            <span
              tabIndex={0}
              className={clsx("inline-flex h-6 cursor-help items-center gap-1 rounded-md border px-2 text-[12px]", tone === "bad" ? "border-bad/30 text-bad" : "border-line text-fg-2 hover:text-fg")}
            >
              {humanize(family)}
              {variant !== "base" && <span className="ident text-[11px] opacity-75">· {variant}</span>}
            </span>
          </VariantCard>
        );
      })}
    </span>
  );
}

function Expanded({ config, views, selection }: { config: ModelConfig; views: RunView[]; selection: RunSelection }) {
  const families = groupCases(config.cases);
  const tallies = [...config.perCase.values()];
  const never = tallies.filter((t) => t.known > 0 && t.passed === 0).map((t) => t.case);
  const flipped = tallies.filter((t) => t.passed > 0 && t.failed > 0).map((t) => t.case);
  const newest = [...views].reverse();
  return (
    <div className="grid gap-3 pb-4 lg:pl-[40px]">
      <div className="relative overflow-x-auto rounded-md border border-line">
        <table className="w-full min-w-[820px] text-[12.5px]">
          <thead>
            <tr className="label text-left !text-[10px] [&>th]:h-8 [&>th]:border-b [&>th]:border-line [&>th]:px-3 [&>th]:font-medium">
              <th className="w-8">
                <span className="sr-only">Select</span>
              </th>
              <th>Run</th>
              <th>
                <Tip content="One square per case in suite order, grouped by scenario. Hover a square for its case.">
                  <span tabIndex={0} className={HINT}>
                    Cases
                  </span>
                </Tip>
              </th>
              <th>Ground Truth</th>
              <th className="text-right">Unknown</th>
              <th className="text-right">Verifier</th>
              <th className="text-right">Duration</th>
              <th className="text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {newest.map((view) => {
              const { run } = view;
              const on = selection.has(view.ref);
              return (
                <tr key={view.ref} className={clsx("border-b border-line last:border-b-0", on ? "bg-accent-soft" : "hover:bg-surface-2/60")}>
                  <td className="px-3">
                    <SelectBox checked={on} disabled={selection.full} onChange={() => selection.toggle(view.ref)} label={`Select run ${run.run_id} for comparison`} />
                  </td>
                  <td className="px-3 py-1.5 whitespace-nowrap">
                    <span className="inline-flex items-center gap-2">
                      <Link to={`/runs/${view.ref}`} className="text-fg hover:underline hover:decoration-line-strong hover:underline-offset-2">
                        {runDate(run.run_id)}
                      </Link>
                      {run.status === "incomplete" && <IncompleteTag run={run} />}
                    </span>
                  </td>
                  <td className="px-3">
                    <CaseSquares view={view} families={families} />
                  </td>
                  <td className="px-3 whitespace-nowrap" title={gtTip(run)}>
                    <span className="num font-medium">{pct(run.ground_truth_rate)}</span>{" "}
                    <span className="num text-fg-3">
                      {run.ground_truth_passed}/{run.ground_truth_known}
                    </span>
                  </td>
                  <td className={clsx("num px-3 text-right", run.ground_truth_unavailable ? "text-warn" : "text-fg-3")}>{run.ground_truth_unavailable}</td>
                  <td className="num px-3 text-right text-fg-2">{pct(view.verifierRate, 0)}</td>
                  <td className="num px-3 text-right text-fg-2">{duration(run.duration_s)}</td>
                  <td className="num px-3 text-right text-fg-2">{usd(run.total_cost)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <dl className="grid gap-2 text-[12.5px] sm:grid-cols-[150px_minmax(0,1fr)] sm:gap-x-4">
        <dt className="text-fg-3">Never passed</dt>
        <dd>{never.length ? <CaseList ids={never} tone="bad" /> : <span className="text-fg-3">None</span>}</dd>
        <dt className="text-fg-3">Changed between runs</dt>
        <dd>
          {config.runs.length < 2 ? (
            <span className="text-fg-3">One run; no repetition to compare.</span>
          ) : flipped.length ? (
            <>
              <span className="num mr-2 text-fg">{flipped.length}</span>
              <CaseList ids={flipped} tone="neutral" />
            </>
          ) : (
            <span className="text-fg-3">Every case kept its Ground Truth outcome across runs.</span>
          )}
        </dd>
      </dl>
    </div>
  );
}

function ConfigRow({ config, views, selection, open, onToggle }: { config: ModelConfig; views: RunView[]; selection: RunSelection; open: boolean; onToggle: () => void }) {
  const navigate = useNavigate();
  const spread = spreadOf(config);
  const chrono = [...views].sort((a, b) => a.run.run_id.localeCompare(b.run.run_id));
  const label = chrono[chrono.length - 1];
  const refs = config.runs.map((r) => r.ref);
  const picked = refs.filter((ref) => selection.has(ref)).length;
  const compareRefs = refs.slice(0, MAX_COMPARE);
  const panelId = `config-${config.slug}`;
  return (
    <li className={clsx("border-b border-line last:border-b-0", open && "bg-surface-2/30")}>
      <div className="grid grid-cols-[28px_minmax(0,1fr)] items-center gap-x-3 gap-y-2.5 py-3 pr-4 pl-2 lg:grid-cols-[28px_minmax(220px,1.25fr)_minmax(150px,1fr)_118px_84px_80px_84px_150px]">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-controls={panelId}
          aria-label={`${open ? "Collapse" : "Expand"} runs of ${config.debug}, ${techniqueLabel(config.technique)}`}
          className="grid size-7 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2 hover:text-fg"
        >
          <ChevronRight className={clsx("size-4 transition-transform motion-reduce:transition-none", open && "rotate-90")} strokeWidth={1.75} />
        </button>
        <div className="min-w-0">
          {label && <RunModel view={label} className="text-[13px] font-medium" />}
          <div
            className="mt-0.5 truncate pl-[21px] text-[12px] text-fg-3"
            title={`Knowledge ${config.api} · verifier ${config.verification}${config.incompleteRuns ? ` · ${config.incompleteRuns} incomplete ${config.incompleteRuns === 1 ? "run" : "runs"}` : ""}`}
          >
            {techniqueLabel(config.technique)} · {config.runs.length} {config.runs.length === 1 ? "run" : "runs"} · {config.cases.length} cases
          </div>
        </div>
        <div className="col-start-2 flex flex-wrap items-center gap-x-6 gap-y-2.5 lg:contents">
          <div className="min-w-0">
            <RunStrip views={chrono} selection={selection} />
          </div>
          <div title={`${config.passed} of ${config.known} known attempts passed${config.unknown ? `; ${config.unknown} unknown` : ""}`}>
            <div className="flex items-center gap-2">
              <RateBar rate={config.rate} width={40} />
              <span className="num text-[13px] font-medium">{pct(config.rate)}</span>
            </div>
            <div className="num mt-0.5 text-[11.5px] text-fg-3">
              {count(config.passed)}/{count(config.known)}
              {config.unknown > 0 && <span className="text-warn"> · {config.unknown} unk.</span>}
            </div>
          </div>
          <Metric label="Spread" value={spread ? (spread.n > 1 ? `${pct(spread.min, 0)}–${pct(spread.max, 0)}` : pct(spread.min, 0)) : "—"} hint="Lowest to highest Ground Truth success across this configuration's runs." />
          <Metric label="Time" value={duration(config.medianAttemptS)} hint="Median time per attempt" />
          <Metric
            label="Cost"
            value={usd(config.costPerAttempt)}
            hint={config.costRuns ? `Per attempt, over ${config.costRuns} of ${config.runs.length} runs that recorded cost` : "No run recorded cost"}
          />
          <div className="flex items-center gap-1.5 lg:justify-end">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => (picked === refs.length ? refs.forEach((ref) => selection.has(ref) && selection.toggle(ref)) : selection.add(refs))}
              disabled={picked < refs.length && selection.full}
            >
              {picked === refs.length ? "Deselect" : picked ? `Add rest` : "Select all"}
            </Button>
            {refs.length >= 2 && (
              <Tip content={refs.length > MAX_COMPARE ? `Compare the latest ${MAX_COMPARE} runs of this configuration` : "Compare these repetitions with each other"}>
                <Button size="sm" onClick={() => navigate(compareHref(compareRefs))}>
                  Compare <ArrowRight className="size-3.5" strokeWidth={2} />
                </Button>
              </Tip>
            )}
          </div>
        </div>
      </div>
      {open && (
        <div id={panelId} className="px-4">
          <Expanded config={config} views={chrono} selection={selection} />
        </div>
      )}
    </li>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div title={hint}>
      <div className="label !text-[9.5px] lg:hidden">{label}</div>
      <div className="num text-[12.5px] text-fg-2">{value}</div>
    </div>
  );
}

function SectionHead({ source, configs }: { source: RunSource; configs: ModelConfig[] }) {
  const runs = configs.reduce((sum, c) => sum + c.runs.length, 0);
  const one = (values: string[]) => new Set(values).size === 1;
  const suite = new Set(configs.flatMap((c) => c.cases)).size;
  const comparable = one(configs.map((c) => c.api)) && one(configs.map((c) => c.verification)) && one(configs.map((c) => c.technique ?? "")) && configs.every((c) => c.cases.length === suite);
  return (
    <header className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-line px-4 py-2.5">
      <h2 className="text-[13.5px] font-medium">{SOURCE_LABEL[source]}</h2>
      <span className="num text-[12.5px] text-fg-3">
        {configs.length} {configs.length === 1 ? "configuration" : "configurations"} · {runs} runs
      </span>
      {configs.length > 1 &&
        (comparable ? (
          <Tip content="Same cases, knowledge model, verifier, and technique: differences come from the debug model.">
            <span tabIndex={0}>
              <Tag tone="accent">Comparable</Tag>
            </span>
          </Tip>
        ) : (
          <Tip content="Configurations here differ in technique, case set, or models. Compare within matching settings before attributing a difference.">
            <span tabIndex={0}>
              <Tag tone="warn">Mixed settings</Tag>
            </span>
          </Tip>
        ))}
    </header>
  );
}

export default function Configurations() {
  const { views, byRef, configs, isLoading, error } = useRunViews();
  const selection = useRunSelection();
  const [query, setQuery] = useState("");
  const [source, setSource] = useState<"all" | RunSource>("all");
  const [sort, setSort] = useState<SortKey>("rate");
  const [open, setOpen] = useState<Set<string>>(new Set());

  const viewsOf = useMemo(() => {
    const map = new Map<string, RunView[]>();
    for (const view of views) if (view.config) map.set(view.config.key, [...(map.get(view.config.key) ?? []), view]);
    return map;
  }, [views]);

  const sections = useMemo(() => {
    const visible = configs.filter((config) => (source === "all" || config.source === source) && (viewsOf.get(config.key) ?? []).some((view) => matchesQuery(view, query)));
    const sorted = [...visible].sort((a, b) =>
      sort === "rate" ? (b.rate ?? -1) - (a.rate ?? -1) || b.known - a.known : sort === "latest" ? latestId(b).localeCompare(latestId(a)) : b.runs.length - a.runs.length || latestId(b).localeCompare(latestId(a)),
    );
    return (["canonical", "exploratory", "local"] as RunSource[]).map((s) => ({ source: s, configs: sorted.filter((c) => c.source === s) })).filter((s) => s.configs.length);
  }, [configs, viewsOf, source, query, sort]);

  if (isLoading) return <LoadingState label="Reading recorded runs" />;
  if (error) return <ErrorState error={error} />;

  const latestCanonical = configs.filter((c) => c.source === "canonical").map((c) => c.runs[0]?.ref).filter((ref): ref is string => !!ref);
  const toggle = (key: string) => setOpen((current) => {
    const next = new Set(current);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });
  const shownConfigs = sections.reduce((sum, s) => sum + s.configs.length, 0);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <SearchField value={query} onChange={setQuery} placeholder="Search models, techniques, runs" className="w-full sm:w-72" />
        <Segmented
          label="Source"
          value={source}
          onChange={setSource}
          options={[{ value: "all", label: "All" }, ...(["canonical", "exploratory", "local"] as RunSource[]).filter((s) => configs.some((c) => c.source === s)).map((s) => ({ value: s, label: SOURCE_LABEL[s] }))]}
        />
        <Segmented
          label="Sort configurations"
          value={sort}
          onChange={setSort}
          options={[
            { value: "rate", label: "Success", hint: "Pooled Ground Truth success, highest first" },
            { value: "latest", label: "Latest", hint: "Most recent run first" },
            { value: "runs", label: "Runs", hint: "Most runs first" },
          ]}
        />
        <div className="ml-auto flex items-center gap-2">
          <Tip content="Selects the newest run of every canonical configuration: one repetition per model on the same 27 cases.">
            <Button size="sm" onClick={() => selection.set(latestCanonical)} disabled={latestCanonical.length < 2}>
              Latest canonical run per model
            </Button>
          </Tip>
        </div>
      </div>

      <div className="rounded-lg border border-line bg-surface">
        <div className="label hidden grid-cols-[28px_minmax(220px,1.25fr)_minmax(150px,1fr)_118px_84px_80px_84px_150px] gap-x-3 border-b border-line py-2.5 pr-4 pl-2 !text-[10px] lg:grid">
          <span />
          <span>Configuration</span>
          <span>Runs, oldest first</span>
          <span>Ground Truth</span>
          <span>Spread</span>
          <span>Time</span>
          <span>Cost</span>
          <span className="text-right">
            {count(shownConfigs)} of {count(configs.length)}
          </span>
        </div>
        {sections.map((section) => (
          <section key={section.source} aria-label={SOURCE_LABEL[section.source]}>
            <SectionHead source={section.source} configs={section.configs} />
            <ul>
              {section.configs.map((config) => (
                <ConfigRow key={config.key} config={config} views={viewsOf.get(config.key) ?? []} selection={selection} open={open.has(config.key)} onToggle={() => toggle(config.key)} />
              ))}
            </ul>
          </section>
        ))}
        {sections.length === 0 && <p className="px-4 py-12 text-center text-[13px] text-fg-3">No configuration has a run matching this search.</p>}
        <p className="border-t border-line px-4 py-2.5 text-[12px] text-fg-3">
          A configuration is one debug model under one knowledge model, verifier, technique, and source; its runs are repetitions. Bars are each run's Ground Truth success; an amber cap marks an incomplete run.
        </p>
      </div>

      <CompareTray selection={selection} byRef={byRef} />
    </div>
  );
}
