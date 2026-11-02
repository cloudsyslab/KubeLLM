import clsx from "clsx";
import { ArrowDown, ArrowUp, ChevronRight } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { techniqueLabel, type ModelConfig } from "@/lib/explore";
import { compact, count, duration, pct, usd } from "@/lib/format";
import { ModelName, RunStrip } from "./charts";
import { ModelCard } from "./ModelCard";
import { Tag, Tip } from "./ui";

type SortKey = "rate" | "known" | "verify" | "time" | "cost" | "tokens";

const COLUMNS: { key: SortKey; label: string; hint: string; value: (c: ModelConfig) => number | null; better: "higher" | "lower" }[] = [
  { key: "rate", label: "Ground Truth", hint: "Share of attempts with a known Ground Truth outcome that passed. Unknown outcomes are excluded from the denominator and counted separately.", value: (c) => c.rate, better: "higher" },
  { key: "known", label: "Known / attempts", hint: "Attempts with a recorded Ground Truth outcome, out of all observed attempts.", value: (c) => c.known, better: "higher" },
  { key: "verify", label: "Verifier agrees", hint: "How often the independent Verification judgment matched Ground Truth. A separate signal, never proof of success.", value: (c) => c.verifyAgree, better: "higher" },
  { key: "time", label: "Time / attempt", hint: "Median wall-clock time of one case attempt, including knowledge, debug, and verification phases.", value: (c) => c.medianAttemptS, better: "lower" },
  { key: "cost", label: "Cost / attempt", hint: "Recorded API cost divided by observed attempts, over runs that recorded cost. Missing cost is not zero.", value: (c) => c.costPerAttempt, better: "lower" },
  { key: "tokens", label: "Tokens / attempt", hint: "Recorded tokens across all agent roles divided by observed attempts.", value: (c) => c.tokensPerAttempt, better: "lower" },
];

function Header({ children, hint, sorted, dir, onClick, align = "right" }: { children: ReactNode; hint?: string; sorted?: boolean; dir?: "asc" | "desc"; onClick?: () => void; align?: "left" | "right" }) {
  const inner = (
    <button type="button" onClick={onClick} className={clsx("inline-flex cursor-pointer items-center gap-1 hover:text-fg", sorted && "text-fg", align === "right" && "flex-row-reverse")}>
      <span>{children}</span>
      {sorted ? dir === "asc" ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" /> : <span className="size-3" />}
    </button>
  );
  return (
    <th scope="col" aria-sort={sorted ? (dir === "asc" ? "ascending" : "descending") : undefined} className={clsx("label h-11 border-b border-line px-3 !text-[10.5px] !leading-tight font-medium", align === "right" ? "text-right" : "text-left")}>
      {hint ? <Tip content={hint}>{inner}</Tip> : inner}
    </th>
  );
}

export function Leaderboard({ configs, hovered, onHover }: { configs: ModelConfig[]; hovered: string | null; onHover: (key: string | null) => void }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "rate", dir: "desc" });
  const mixedTechniques = new Set(configs.map((c) => c.technique)).size > 1;
  const rows = useMemo(() => {
    const column = COLUMNS.find((c) => c.key === sort.key)!;
    return [...configs].sort((a, b) => {
      const av = column.value(a);
      const bv = column.value(b);
      if (av === null) return 1;
      if (bv === null) return -1;
      return sort.dir === "asc" ? av - bv : bv - av;
    });
  }, [configs, sort]);

  const toggle = (key: SortKey) => {
    const column = COLUMNS.find((c) => c.key === key)!;
    setSort((current) => (current.key === key ? { key, dir: current.dir === "asc" ? "desc" : "asc" } : { key, dir: column.better === "higher" ? "desc" : "asc" }));
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[960px] border-collapse text-[13px]">
        <thead>
          <tr>
            <th scope="col" className="label hidden h-9 w-10 border-b border-line pl-4 text-left !text-[10.5px] font-medium sm:table-cell">#</th>
            <th scope="col" className="label sticky left-0 z-10 h-9 border-b border-line bg-surface px-3 text-left !text-[10.5px] font-medium sm:static sm:bg-transparent">Model</th>
            {COLUMNS.map((column) => (
              <Header key={column.key} hint={column.hint} sorted={sort.key === column.key} dir={sort.dir} onClick={() => toggle(column.key)}>
                {column.label}
              </Header>
            ))}
            <th scope="col" className="w-10 border-b border-line" aria-label="Open" />
          </tr>
        </thead>
        <tbody onMouseLeave={() => onHover(null)}>
          {rows.map((config, index) => (
            <tr
              key={config.key}
              onMouseEnter={() => onHover(config.key)}
              className={clsx("group border-b border-line transition-colors last:border-b-0", hovered === config.key ? "bg-surface-2" : "hover:bg-surface-2/60")}
            >
              <td className="num hidden pl-4 text-[12px] text-fg-3 sm:table-cell">{index + 1}</td>
              <td className="sticky left-0 z-10 bg-surface px-3 py-2.5 sm:static sm:bg-transparent">
                <ModelCard config={config} side="right">
                <Link to={`/models/${config.slug}`} className="block min-w-0 focus-visible:outline-offset-4">
                  <ModelName config={config} className="text-[13px] font-medium" />
                  <div className="mt-0.5 flex items-center gap-1.5 pl-[21px] text-[12px] text-fg-3">
                    {mixedTechniques && (
                      <>
                        <span>{techniqueLabel(config.technique)}</span>
                        <span aria-hidden>·</span>
                      </>
                    )}
                    <span>
                      {config.runs.length} {config.runs.length === 1 ? "run" : "runs"} · {config.cases.length} cases
                    </span>
                    {config.source !== "canonical" && <Tag className="ml-1">{config.source}</Tag>}
                  </div>
                </Link>
                </ModelCard>
              </td>
              <td className="px-3 py-2.5 text-right">
                <div className="inline-flex items-center gap-3">
                  {config.runRates.length > 1 && (
                    <span className="hidden sm:inline">
                      <RunStrip config={config} width={88} />
                    </span>
                  )}
                  <span className="num w-[52px] text-[14px] font-medium">{pct(config.rate)}</span>
                </div>
              </td>
              <td className="px-3 py-2.5 text-right">
                <div className="num text-fg-2">
                  {count(config.known)} <span className="text-fg-3">/ {count(config.attempts)}</span>
                </div>
                {config.unknown > 0 && <div className="mt-0.5 text-[11.5px] text-warn">{config.unknown} unknown</div>}
              </td>
              <td className="num px-3 py-2.5 text-right text-fg-2">{pct(config.verifyAgree, 0)}</td>
              <td className="num px-3 py-2.5 text-right text-fg-2">{duration(config.medianAttemptS)}</td>
              <td className="px-3 py-2.5 text-right">
                <div className="num text-fg-2">{usd(config.costPerAttempt)}</div>
                {config.costRuns > 0 && config.costRuns < config.runs.length && (
                  <div className="mt-0.5 text-[11.5px] text-fg-3">
                    {config.costRuns}/{config.runs.length} runs
                  </div>
                )}
              </td>
              <td className="num px-3 py-2.5 text-right text-fg-2">{compact(config.tokensPerAttempt)}</td>
              <td className="pr-3 text-right">
                <Link to={`/models/${config.slug}`} aria-label={`Open ${config.debug}`} className="inline-grid size-6 place-items-center rounded text-fg-3 group-hover:text-fg">
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
