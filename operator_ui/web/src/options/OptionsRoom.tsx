import clsx from "clsx";
import { ArrowUpRight, Check } from "lucide-react";
import { Suspense } from "react";
import { Link, useSearchParams } from "react-router";
import { PageHeader, Tag } from "@/components/ui";
import { ReplayBar } from "@/demo/ReplayBar";
import { useOptionChoice } from "./choice";
import { PickSheet } from "./PickSheet";
import { SURFACES, surfaceDef, type OptionDef, type Surface } from "./registry";

export function StageFallback() {
  return <div className="h-[560px] animate-pulse rounded-lg bg-surface" />;
}

function OptionCard({ option, shown, chosen, onShow, onChoose }: { option: OptionDef; shown: boolean; chosen: boolean; onShow: () => void; onChoose: () => void }) {
  return (
    <div
      className={clsx(
        "flex min-w-0 flex-col gap-3 rounded-lg border bg-surface p-4 transition-colors",
        shown ? "border-accent-line" : "border-line hover:border-line-strong",
      )}
    >
      <button type="button" onClick={onShow} aria-pressed={shown} className="grid cursor-pointer gap-2 text-left">
        <div className="flex items-center gap-2">
          <span className={clsx("grid size-6 place-items-center rounded-md font-mono text-[12px] font-medium", shown ? "bg-accent text-accent-ink" : "bg-surface-3 text-fg-2")}>{option.letter}</span>
          <span className="text-[14px] font-medium">{option.name}</span>
          {option.recommended && <Tag tone="accent" className="ml-auto">Recommended</Tag>}
        </div>
        <p className="text-[13px] leading-relaxed text-fg-2">{option.idea}</p>
      </button>
      <dl className="mt-auto grid gap-1.5 text-[12.5px]">
        <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
          <dt className="text-fg-3">Best for</dt>
          <dd className="text-fg-2">{option.optimizes}</dd>
        </div>
        <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
          <dt className="text-fg-3">Costs</dt>
          <dd className="text-fg-2">{option.tradeoff}</dd>
        </div>
        <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
          <dt className="text-fg-3">Pattern</dt>
          <dd className="text-fg-2">{option.reference}</dd>
        </div>
      </dl>
      <button
        type="button"
        onClick={onChoose}
        className={clsx(
          "inline-flex h-8 cursor-pointer items-center justify-center gap-1.5 rounded-md text-[13px] font-medium transition-colors",
          chosen ? "bg-accent-soft text-accent" : "border border-line-strong text-fg hover:bg-surface-2",
        )}
      >
        {chosen ? (
          <>
            <Check className="size-3.5" strokeWidth={2.25} /> Shown on the page
          </>
        ) : (
          "Use on the page"
        )}
      </button>
    </div>
  );
}

function SurfaceRoom({ surface }: { surface: Surface }) {
  const def = surfaceDef(surface);
  const [params, setParams] = useSearchParams();
  const [chosen, choose] = useOptionChoice(surface);
  const shown = def.options.find((o) => o.id === params.get("option")) ?? chosen;
  const Stage = shown.component;
  const show = (id: string) => setParams({ surface, option: id }, { replace: true });

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-[17px] font-medium tracking-[-0.01em]">{def.question}</h2>
        {def.path ? (
          <Link to={def.path} className="inline-flex items-center gap-1 text-[13px] text-fg-3 hover:text-fg">
            Open the {def.label} page <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
          </Link>
        ) : (
          <span className="text-[13px] text-fg-3">Shown on every page once picked</span>
        )}
      </div>
      <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        {def.options.map((option) => (
          <OptionCard key={option.id} option={option} shown={shown.id === option.id} chosen={chosen.id === option.id} onShow={() => show(option.id)} onChoose={() => choose(option.id)} />
        ))}
      </div>
      <div className="grid gap-2">
        <div className="flex items-center gap-2 text-[12.5px] text-fg-3">
          <span className="font-mono text-fg-2">
            {def.label} · {shown.letter}
          </span>
          <span>{shown.name}</span>
        </div>
        <Suspense fallback={<StageFallback />}>
          <Stage key={shown.id} />
        </Suspense>
      </div>
    </div>
  );
}

/** Surfaces driven by the shared demo campaign show the replay controls. */
export const LIVE_SURFACES = new Set<Surface>(["execution", "resources", "topology", "jobs", "dock"]);

function SurfaceNav({ value, onChange }: { value: Surface | "overview"; onChange: (next: Surface | "overview") => void }) {
  const groups = [...new Set(SURFACES.map((s) => s.group))];
  const item = (id: Surface | "overview", label: string, count?: number) => (
    <button
      key={id}
      type="button"
      aria-pressed={value === id}
      onClick={() => onChange(id)}
      className={clsx(
        "inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 rounded-md px-2.5 text-[13px] transition-colors",
        value === id ? "bg-surface-3 text-fg" : "text-fg-3 hover:bg-surface-2 hover:text-fg",
      )}
    >
      {label}
      {count !== undefined && <span className="num text-[11px] text-fg-3">{count}</span>}
    </button>
  );
  return (
    <nav aria-label="Surfaces" className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 pb-1">
      {item("overview", "Overview")}
      {groups.map((group) => (
        <div key={group} className="flex items-center gap-1">
          <span className="label ml-3 mr-1 shrink-0 !text-[10px]">{group}</span>
          {SURFACES.filter((s) => s.group === group).map((s) => item(s.id, s.label, s.options.length))}
        </div>
      ))}
    </nav>
  );
}

export function OptionsRoomPage() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("surface");
  const surface = (SURFACES.find((s) => s.id === requested)?.id ?? "overview") as Surface | "overview";
  const total = SURFACES.reduce((sum, s) => sum + s.options.length, 0);
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Design review"
        title="Options room"
        description={`${total} options across ${SURFACES.length} surfaces, each rendered with the same demo data. Compare them, then pick one per surface; your pick is what its page shows.`}
      />
      <SurfaceNav value={surface} onChange={(next) => setParams(next === "overview" ? {} : { surface: next }, { replace: true })} />
      {surface === "overview" ? (
        <Suspense fallback={<StageFallback />}>
          <PickSheet />
        </Suspense>
      ) : (
        <>
          {LIVE_SURFACES.has(surface) && <ReplayBar />}
          <SurfaceRoom key={surface} surface={surface} />
        </>
      )}
    </div>
  );
}

export function SurfacePage({ surface }: { surface: Surface }) {
  const [option] = useOptionChoice(surface);
  const def = surfaceDef(surface);
  const Stage = option.component;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={def.group}
        title={def.title}
        description={def.description}
        actions={
          <Link to={`/options?surface=${surface}`} className="inline-flex h-8 items-center gap-2 rounded-md border border-line px-3 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg">
            <span className="font-mono text-fg-3">{option.letter}</span>
            {option.name}
            <span className="text-fg-3">· compare {def.options.length} options</span>
          </Link>
        }
      />
      {LIVE_SURFACES.has(surface) && <ReplayBar />}
      <Suspense fallback={<StageFallback />}>
        <Stage key={option.id} />
      </Suspense>
    </div>
  );
}
