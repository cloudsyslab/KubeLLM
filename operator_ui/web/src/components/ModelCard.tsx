import { ArrowUpRight } from "lucide-react";
import { HoverCard } from "radix-ui";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { labOf, modelInfo, type Lab } from "@/data/models";
import { techniqueLabel, type ModelConfig } from "@/lib/explore";
import { duration, pct } from "@/lib/format";
import { displayModel } from "./charts";
import { Tag } from "./ui";

// Brand mark in the lab's own color. Labs without a sourced logo get a neutral
// monogram rather than an invented mark.
export function LabLogo({ lab, size = 14, className }: { lab: Lab | undefined; size?: number; className?: string }) {
  if (lab?.svg) {
    return (
      <span
        aria-hidden
        className={className}
        style={{ display: "inline-grid", placeItems: "center", width: size, height: size, flexShrink: 0, fontSize: size, lineHeight: 1, color: lab.color ?? "var(--fg)" }}
        dangerouslySetInnerHTML={{ __html: lab.svg }}
      />
    );
  }
  return (
    <span
      aria-hidden
      className={className}
      style={{ display: "inline-grid", placeItems: "center", width: size, height: size, flexShrink: 0, borderRadius: 3, background: "var(--surface-3)", color: "var(--fg-2)", fontSize: size * 0.62, fontWeight: 600, lineHeight: 1 }}
    >
      {(lab?.name ?? "?").slice(0, 1)}
    </span>
  );
}

function Fact({ label, value }: { label: string; value?: ReactNode }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-2 text-[12.5px]">
      <dt className="text-fg-3">{label}</dt>
      <dd className="text-fg">{value}</dd>
    </div>
  );
}

export function ModelCardBody({ config }: { config: ModelConfig }) {
  const info = modelInfo(config.debug);
  const lab = labOf(config.debug);
  return (
    <div className="grid gap-3">
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-md border border-line bg-surface">
          <LabLogo lab={lab} size={20} />
        </span>
        <div className="min-w-0">
          <div className="text-[12.5px] text-fg-2">{lab?.name ?? "Lab unconfirmed"}</div>
          <div className="ident truncate text-[15px] leading-tight font-medium text-fg">{displayModel(config.debug)}</div>
        </div>
      </div>
      {(info?.tier || info?.weights) && (
        <div className="flex flex-wrap gap-1.5">
          {info?.tier && <Tag>{info.tier}</Tag>}
          {info?.weights && <Tag>{info.weights}</Tag>}
        </div>
      )}
      {info?.summary && <p className="text-[12.5px] leading-relaxed text-fg-2">{info.summary}</p>}
      <dl className="grid gap-1.5">
        <Fact label="Family" value={info?.family} />
        <Fact label="Released" value={info?.released} />
        <Fact label="Size" value={info?.size} />
        <Fact label="License" value={info?.license} />
        <Fact label="Served" value={info?.served} />
      </dl>
      <div className="grid gap-1 border-t border-line pt-3 text-[12.5px]">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-fg-3">This benchmark</span>
          <span className="text-fg-3">{techniqueLabel(config.technique)}</span>
        </div>
        <div className="num text-fg">
          {pct(config.rate)} Ground Truth · {config.runs.length} {config.runs.length === 1 ? "run" : "runs"} · {duration(config.medianAttemptS)} per attempt
        </div>
      </div>
      {info?.sources && info.sources.length > 0 && (
        <div className="text-[11px] leading-relaxed text-fg-3">
          Sources:{" "}
          {info.sources.map((source, index) => (
            <span key={source.label}>
              {index > 0 && ", "}
              {source.url ? (
                <a href={source.url} target="_blank" rel="noreferrer" className="underline decoration-line-strong underline-offset-2 hover:text-fg-2">
                  {source.label}
                </a>
              ) : (
                source.label
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function ModelCard({ config, children, side = "bottom" }: { config: ModelConfig; children: ReactNode; side?: "top" | "right" | "bottom" | "left" }) {
  return (
    <HoverCard.Root openDelay={300} closeDelay={80}>
      <HoverCard.Trigger asChild>{children}</HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content side={side} align="start" sideOffset={8} collisionPadding={12} className="z-50 w-[min(340px,calc(100vw-24px))] rounded-lg bg-surface-2 p-4 shadow-pop">
          <ModelCardBody config={config} />
          <Link to={`/models/${config.slug}`} className="mt-3 inline-flex items-center gap-1 text-[12.5px] text-fg-2 hover:text-fg">
            Open model <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
          </Link>
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}
