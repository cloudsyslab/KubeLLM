import { useQuery } from "@tanstack/react-query";
import { Coins, Target, Timer } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { api, snapshotGeneratedAt } from "@/api/client";
import { CaseMatrix, MatrixLegend } from "@/components/CaseMatrix";
import { MetricBars } from "@/components/charts";
import { Leaderboard } from "@/components/Leaderboard";
import { ErrorState, LoadingState } from "@/components/states";
import { PageHeader, Panel, Segmented, Tag, Tip } from "@/components/ui";
import { buildConfigs, rankConfigs, suiteCases, techniqueLabel, type ModelConfig, type Scope } from "@/lib/explore";
import { count, duration, pct, usd } from "@/lib/format";

const SCOPES: { value: Scope; label: string; hint: string }[] = [
  { value: "canonical", label: "Canonical", hint: "The seven current benchmark configurations in data/" },
  { value: "exploratory", label: "Exploratory", hint: "Pilots, technique trials, and archived packs in data/exploratory" },
  { value: "all", label: "All", hint: "Every recorded configuration" },
];

function distinct<T>(values: T[]) {
  return [...new Set(values)];
}

function Comparability({ configs, cases }: { configs: ModelConfig[]; cases: string[] }) {
  const apis = distinct(configs.map((c) => c.api));
  const verifiers = distinct(configs.map((c) => c.verification));
  const techniques = distinct(configs.map((c) => c.technique));
  const fullSuite = configs.every((c) => c.cases.length === cases.length);
  const runs = distinct(configs.map((c) => c.runs.length));
  const comparable = apis.length === 1 && verifiers.length === 1 && techniques.length === 1 && fullSuite;

  const facts = comparable
    ? [
        `${cases.length} shared cases`,
        `${techniqueLabel(techniques[0])}`,
        `knowledge model ${apis[0]}`,
        `verifier ${verifiers[0]}`,
        runs.length === 1 ? `${runs[0]} runs each` : `${Math.min(...runs)}–${Math.max(...runs)} runs each`,
      ]
    : [
        `${techniques.length} ${techniques.length === 1 ? "technique" : "techniques"}`,
        `${apis.length} knowledge ${apis.length === 1 ? "model" : "models"}`,
        `${verifiers.length} ${verifiers.length === 1 ? "verifier" : "verifiers"}`,
        `case coverage ${Math.min(...configs.map((c) => c.cases.length))}–${Math.max(...configs.map((c) => c.cases.length))} of ${cases.length}`,
      ];

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-fg-2">
      {comparable ? (
        <Tip content="Every configuration ran the same cases with the same knowledge model, verifier, and technique, so differences come from the debug model.">
          <span>
            <Tag tone="accent">Comparable</Tag>
          </span>
        </Tip>
      ) : (
        <Tip content="Settings differ between these configurations. Compare rows that share a technique and case set before attributing a difference to the model.">
          <span>
            <Tag tone="warn">Mixed settings</Tag>
          </span>
        </Tip>
      )}
      {facts.map((fact, index) => (
        <span key={fact} className="flex items-center gap-3">
          {index > 0 && <span className="text-fg-3/60" aria-hidden>·</span>}
          <span className={fact.includes("model") || fact.includes("verifier") ? "" : ""}>{fact}</span>
        </span>
      ))}
    </div>
  );
}

function Totals({ configs }: { configs: ModelConfig[] }) {
  const { data: generatedAt } = useQuery({ queryKey: ["snapshot-date"], queryFn: snapshotGeneratedAt });
  const runs = configs.reduce((sum, c) => sum + c.runs.length, 0);
  const attempts = configs.reduce((sum, c) => sum + c.attempts, 0);
  const known = configs.reduce((sum, c) => sum + c.known, 0);
  const items: [string, string][] = [
    ["Configurations", count(configs.length)],
    ["Runs", count(runs)],
    ["Attempts", count(attempts)],
    ["Known outcomes", `${count(known)} · ${pct(attempts ? known / attempts : null, 0)}`],
  ];
  if (generatedAt) items.push(["Snapshot", new Date(generatedAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })]);
  return (
    <dl className="flex flex-wrap gap-x-8 gap-y-3">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="label !text-[10px]">{label}</dt>
          <dd className="num mt-1 text-[15px] font-medium tracking-[-0.01em]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ModelsPage() {
  const query = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const [params, setParams] = useSearchParams();
  const scope = (SCOPES.find((s) => s.value === params.get("scope"))?.value ?? "canonical") as Scope;
  const [hovered, setHovered] = useState<string | null>(null);
  const navigate = useNavigate();

  const configs = useMemo(() => rankConfigs(buildConfigs(query.data ?? [], scope)), [query.data, scope]);
  const cases = useMemo(() => suiteCases(configs), [configs]);
  const maxRuns = Math.max(0, ...configs.map((c) => c.runs.length));
  const open = (config: ModelConfig) => navigate(`/models/${config.slug}`);

  return (
    <div className="grid gap-8">
      <PageHeader
        eyebrow="Evaluate"
        title="Models"
        description="How often each debug model repairs the broken cluster, measured by Ground Truth, and what each attempt costs in time and money."
        actions={
          <Segmented
            label="Run source"
            value={scope}
            onChange={(next) => setParams(next === "canonical" ? {} : { scope: next }, { replace: true })}
            options={SCOPES}
          />
        }
      />

      {query.isLoading ? (
        <LoadingState label="Reading recorded runs" />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : configs.length === 0 ? (
        <ErrorState error={new Error("No recorded runs match this source.")} />
      ) : (
        <>
          <div className="grid gap-4 border-y border-line py-4">
            <Totals configs={configs} />
            <Comparability configs={configs} cases={cases} />
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <MetricBars
              className="md:col-span-2 xl:col-span-1"
              title="Ground Truth success"
              icon={<Target className="size-4" strokeWidth={1.75} />}
              direction="higher"
              configs={configs}
              value={(c) => c.rate}
              format={(v) => pct(v)}
              domainMax={1}
              detail={(c) => {
                const rates = c.runRates.filter((r) => r.rate !== null).map((r) => r.rate as number);
                const range = rates.length > 1 ? ` · runs ranged ${pct(Math.min(...rates), 0)}–${pct(Math.max(...rates), 0)}` : "";
                return `${count(c.passed)} of ${count(c.known)} known attempts${c.unknown ? ` · ${c.unknown} unknown` : ""}${range}`;
              }}
              hovered={hovered}
              onHover={setHovered}
              onSelect={open}
              footnote="Share of attempts with a known outcome that passed. Unknown outcomes are left out of the rate."
            />
            <MetricBars
              title="Time per attempt"
              icon={<Timer className="size-4" strokeWidth={1.75} />}
              direction="lower"
              configs={configs}
              value={(c) => c.medianAttemptS}
              format={(v) => duration(v)}
              detail={(c) => `Median of ${count(c.attempts)} attempts`}
              hovered={hovered}
              onHover={setHovered}
              onSelect={open}
              footnote="Median wall-clock time for one case, all agent phases included."
            />
            <MetricBars
              title="Cost per attempt"
              icon={<Coins className="size-4" strokeWidth={1.75} />}
              direction="lower"
              configs={configs}
              value={(c) => c.costPerAttempt}
              format={(v) => usd(v)}
              detail={(c) => (c.costRuns ? `${c.costRuns} of ${c.runs.length} runs recorded cost` : "No run recorded cost")}
              hovered={hovered}
              onHover={setHovered}
              onSelect={open}
              footnote="Recorded API cost per attempt. Missing cost shows as a dash, never zero."
            />
          </div>

          <Panel
            title="Leaderboard"
            caption="Every configuration in this source. Each dot in the spread is one run's Ground Truth success."
            flush
          >
            <Leaderboard configs={configs} hovered={hovered} onHover={setHovered} />
          </Panel>

          <Panel
            title="Cases"
            caption={`Ground Truth passes per case, out of each model's runs. Select a cell to open those attempts.`}
            actions={<MatrixLegend runs={maxRuns} />}
          >
            <CaseMatrix configs={configs} cases={cases} />
          </Panel>
        </>
      )}
    </div>
  );
}
