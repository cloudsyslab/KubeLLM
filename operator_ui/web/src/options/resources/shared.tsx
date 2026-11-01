import { area, line } from "d3-shape";
import clsx from "clsx";
import { useMemo } from "react";
import { historyAt, processesAt, sampleAt, threadLoadsAt, type ProcessRow } from "@/demo/lab";
import { useReplay } from "@/demo/replay";
import { Tag, Tip } from "@/components/ui";

export function useLab(points = 90, every = 2) {
  const { campaign, t } = useReplay();
  // Telemetry is sampled every 2 s; recompute only when a new sample lands.
  const tick = Math.floor(t / 2);
  return useMemo(() => {
    if (!campaign) return undefined;
    const at = tick * 2;
    return {
      t: at,
      now: sampleAt(campaign, at),
      history: historyAt(campaign, at, points, every),
      threads: threadLoadsAt(campaign, at),
      processes: processesAt(campaign, at),
    };
  }, [campaign, tick, points, every]);
}

// Responsive SVG without a resize observer: a 100-unit-wide viewBox stretched
// to the container, with strokes that do not scale.
export function Sparkline({ values, max = 1, height = 28, className, stroke = "var(--fg-2)", fill = "var(--track)" }: { values: number[]; max?: number; height?: number; className?: string; stroke?: string; fill?: string }) {
  const x = (i: number) => (i / Math.max(1, values.length - 1)) * 100;
  const y = (v: number) => height - (Math.min(v, max) / max) * (height - 2) - 1;
  const linePath = line<number>().x((_, i) => x(i)).y(y)(values) ?? "";
  const areaPath = area<number>().x((_, i) => x(i)).y0(height).y1(y)(values) ?? "";
  return (
    <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className={clsx("block w-full", className)} style={{ height }} aria-hidden>
      <path d={areaPath} fill={fill} />
      <path d={linePath} fill="none" stroke={stroke} strokeWidth={1.25} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function AreaChart({ series, max, height = 140, gridLines = 3 }: { series: { values: number[]; color: string; label: string }[]; max: number; height?: number; gridLines?: number }) {
  const length = series[0]?.values.length ?? 0;
  const x = (i: number) => (i / Math.max(1, length - 1)) * 100;
  const y = (v: number) => height - (Math.min(v, max) / max) * (height - 4) - 2;
  return (
    <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="block w-full" style={{ height }} role="img" aria-label={series.map((s) => s.label).join(", ")}>
      {Array.from({ length: gridLines + 1 }, (_, i) => {
        const gy = 2 + ((height - 4) / gridLines) * i;
        return <line key={i} x1={0} x2={100} y1={gy} y2={gy} stroke="var(--grid)" strokeWidth={1} vectorEffect="non-scaling-stroke" />;
      })}
      {series.map((s) => (
        <g key={s.label}>
          <path d={area<number>().x((_, i) => x(i)).y0(height).y1(y)(s.values) ?? ""} fill={s.color} opacity={0.12} />
          <path d={line<number>().x((_, i) => x(i)).y(y)(s.values) ?? ""} fill="none" stroke={s.color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
        </g>
      ))}
    </svg>
  );
}

export function Meter({ value, max, tone = "neutral", className }: { value: number; max: number; tone?: "neutral" | "accent" | "warn"; className?: string }) {
  return (
    <div className={clsx("h-1.5 overflow-hidden rounded-full bg-surface-3", className)}>
      <div
        className={clsx("h-full rounded-full transition-[width] duration-500", tone === "warn" ? "bg-warn" : tone === "accent" ? "bg-accent" : "bg-fg-2")}
        style={{ width: `${Math.min(100, (value / max) * 100)}%` }}
      />
    </div>
  );
}

export const RELATION: Record<ProcessRow["attribution"], { word: string; hint: string }> = {
  lane: { word: "Lane", hint: "Owned by the selected lane or the operator app." },
  shared: { word: "Shared", hint: "A shared service. Load can coincide with the campaign without being caused by it." },
  other: { word: "Other account", hint: "Another account's process. Not related to this campaign." },
};

export function Relation({ attribution }: { attribution: ProcessRow["attribution"] }) {
  const meta = RELATION[attribution];
  return (
    <Tip content={meta.hint}>
      <span>
        <Tag tone={attribution === "lane" ? "accent" : "neutral"}>{meta.word}</Tag>
      </span>
    </Tip>
  );
}

export function SourceNote({ children }: { children: React.ReactNode }) {
  return <p className="text-[12px] leading-relaxed text-fg-3">{children}</p>;
}

export const pctText = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`;
