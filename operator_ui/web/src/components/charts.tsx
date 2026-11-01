import clsx from "clsx";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { ReactNode } from "react";
import { labOf } from "@/data/models";
import type { ModelConfig } from "@/lib/explore";
import { pct } from "@/lib/format";
import { LabLogo } from "./ModelCard";
import { Tip } from "./ui";

// Ollama's implicit ":latest" tag adds width without information.
export const displayModel = (id: string) => id.replace(/:latest$/, "");

export const TECHNIQUE_SHORT: Record<string, string> = {
  allStepsAtOnce: "all-at-once",
  stepByStep: "step-by-step",
  singleAgent: "single-agent",
  knowledgeAgentOnly: "KA-only",
};

export const mixedTechniques = (configs: ModelConfig[]) => new Set(configs.map((c) => c.technique)).size > 1;
export const mixedSources = (configs: ModelConfig[]) => new Set(configs.map((c) => c.source)).size > 1;

export function ModelName({ config, className, showSource, showTechnique }: { config: ModelConfig; className?: string; showSource?: boolean; showTechnique?: boolean }) {
  const qualifier = [
    showTechnique ? (TECHNIQUE_SHORT[config.technique ?? ""] ?? "unrecorded") : null,
    showSource && config.source !== "canonical" ? (config.source === "exploratory" ? "expl" : config.source) : null,
  ].filter(Boolean);
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-2", className)}>
      <LabLogo lab={labOf(config.debug)} size={13} />
      <span className="ident truncate text-fg" title={config.debug}>
        {displayModel(config.debug)}
      </span>
      {qualifier.length > 0 && <span className="label shrink-0 !text-[9.5px] !normal-case !tracking-[0.02em]">{qualifier.join(" · ")}</span>}
    </span>
  );
}

interface MetricBarsProps {
  title: string;
  icon: ReactNode;
  direction: "higher" | "lower";
  configs: ModelConfig[];
  value: (config: ModelConfig) => number | null;
  format: (value: number) => string;
  detail?: (config: ModelConfig) => ReactNode;
  domainMax?: number;
  hovered: string | null;
  onHover: (key: string | null) => void;
  onSelect: (config: ModelConfig) => void;
  footnote?: ReactNode;
  className?: string;
}

// Artificial Analysis-style ranked metric: each panel sorts by its own metric so
// the leader is always on top, and hovering a model lights it up in every panel.
export function MetricBars({ title, icon, direction, configs, value, format, detail, domainMax, hovered, onHover, onSelect, footnote, className }: MetricBarsProps) {
  const rows = configs
    .map((config) => ({ config, v: value(config) }))
    .sort((a, b) => (a.v === null ? 1 : b.v === null ? -1 : direction === "higher" ? b.v - a.v : a.v - b.v));
  const max = domainMax ?? Math.max(...rows.map((row) => row.v ?? 0), 0) * 1.08;
  const showTechnique = mixedTechniques(configs);
  const showSource = mixedSources(configs);

  return (
    <figure className={clsx("flex min-w-0 flex-col rounded-lg border border-line bg-surface", className)}>
      <figcaption className="flex items-center gap-2.5 px-4 pt-3.5 pb-3">
        <span className="grid size-7 shrink-0 place-items-center rounded-md bg-surface-3 text-fg-2">{icon}</span>
        <div className="min-w-0">
          <div className="truncate text-[13.5px] leading-5 font-medium">{title}</div>
          <div className="flex items-center gap-1 truncate text-[12px] leading-4 text-fg-3">
            {direction === "higher" ? <ArrowUp className="size-3 shrink-0" strokeWidth={2} /> : <ArrowDown className="size-3 shrink-0" strokeWidth={2} />}
            {direction === "higher" ? "Higher is better" : "Lower is better"}
          </div>
        </div>
      </figcaption>
      <ol className="grid gap-0.5 px-2 pb-2" onMouseLeave={() => onHover(null)}>
        {rows.map(({ config, v }, index) => {
          const active = hovered === config.key;
          const dim = hovered !== null && !active;
          const width = v === null || !max ? 0 : Math.max(1.5, (v / max) * 100);
          return (
            <li key={config.key}>
              <Tip side="right" content={<MetricTip config={config} value={v === null ? "Not recorded" : format(v)} title={title} detail={detail?.(config)} />}>
                <button
                  type="button"
                  onMouseEnter={() => onHover(config.key)}
                  onFocus={() => onHover(config.key)}
                  onClick={() => onSelect(config)}
                  className={clsx(
                    "grid w-full cursor-pointer grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1.5 rounded-md px-2 py-2 text-left transition-[background-color,opacity] duration-150",
                    active ? "bg-surface-2" : "hover:bg-surface-2/60",
                    dim && "opacity-45",
                  )}
                >
                  <span className="num text-[11px] text-fg-3">{index + 1}</span>
                  <ModelName config={config} className="text-[12.5px]" showSource={showSource} showTechnique={showTechnique} />
                  <span className={clsx("num text-right text-[12.5px] font-medium", v === null ? "text-fg-3" : "text-fg")}>{v === null ? "—" : format(v)}</span>
                  <span className="relative col-start-2 col-end-4 h-2 overflow-hidden rounded-full bg-track">
                    {v === null ? (
                      <span className="hatch absolute inset-0 opacity-60" />
                    ) : (
                      <span
                        className="absolute inset-y-0 left-0 rounded-full transition-[width,background-color] duration-300"
                        style={{ width: `${width}%`, background: active ? "var(--accent)" : index === 0 ? "var(--bar)" : "var(--bar-muted)" }}
                      />
                    )}
                  </span>
                </button>
              </Tip>
            </li>
          );
        })}
      </ol>
      {footnote && <div className="mt-auto border-t border-line px-4 py-2.5 text-[12px] text-fg-3">{footnote}</div>}
    </figure>
  );
}

function MetricTip({ config, value, title, detail }: { config: ModelConfig; value: string; title: string; detail?: ReactNode }) {
  return (
    <div className="grid gap-1">
      <div className="ident text-fg">{config.debug}</div>
      <div>
        {title}: <span className="num font-medium text-fg">{value}</span>
      </div>
      {detail && <div className="text-fg-3">{detail}</div>}
      <div className="text-fg-3">Click to open the model and its runs.</div>
    </div>
  );
}

// Each tick is one run's Ground Truth success, so spread is visible without a
// separate chart.
export function RunStrip({ config, width = 96 }: { config: ModelConfig; width?: number }) {
  const rates = config.runRates.filter((run) => run.rate !== null);
  return (
    <span className="relative inline-block h-4 align-middle" style={{ width }} aria-label={`Run spread ${rates.map((run) => pct(run.rate, 0)).join(", ")}`}>
      <span className="absolute inset-x-0 top-1/2 h-px bg-line-strong" />
      {rates.length > 1 && (
        <span
          className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-fg-3/50"
          style={{ left: `${Math.min(...rates.map((r) => r.rate as number)) * 100}%`, width: `${(Math.max(...rates.map((r) => r.rate as number)) - Math.min(...rates.map((r) => r.rate as number))) * 100}%` }}
        />
      )}
      {rates.map((run) => (
        <span key={run.ref} className="absolute top-1/2 size-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-surface bg-fg" style={{ left: `${(run.rate as number) * 100}%` }} />
      ))}
    </span>
  );
}
