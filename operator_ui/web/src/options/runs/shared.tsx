// Shared pieces for the Runs and Compare options: the recorded runs with their
// configuration, run selection (2–8 runs, as /api/compare requires), the
// compare tray, filter menus, and the model label with its hover card.
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight, Check, ChevronDown, GitCompareArrows, Search, X } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { useCallback, useEffect, useMemo, useState, type ReactNode, type Ref } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "@/api/client";
import type { RunSource, RunWithCases } from "@/api/types";
import { displayModel, TECHNIQUE_SHORT } from "@/components/charts";
import { LabLogo, ModelCard } from "@/components/ModelCard";
import { Button, Tag, Tip } from "@/components/ui";
import { labOf } from "@/data/models";
import { buildConfigs, techniqueLabel, type ModelConfig } from "@/lib/explore";
import { runDate } from "@/lib/format";
import { alignment, debugOf, MAX_COMPARE, MIN_COMPARE, type Repetition } from "../compare/model";

export interface RunView {
  run: RunWithCases;
  ref: string;
  /** Start time parsed from the run ID (UTC), if it has one. */
  at: number | null;
  /** Start plus recorded duration. */
  end: number | null;
  debug: string;
  recorded: boolean;
  config: ModelConfig | undefined;
  verifierRate: number | null;
  /** Planned cases with no recorded attempt. */
  missing: number;
}

// Run IDs are ISO-like timestamps (2026-09-23T00-57-28).
export function runTime(runId: string): number | null {
  const match = runId.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})(?:-(\d{2}))?/);
  if (!match) return null;
  const [, y, m, d, hh, mm, ss] = match;
  return Date.UTC(Number(y), Number(m) - 1, Number(d), Number(hh), Number(mm), Number(ss ?? 0));
}

export const verifierRate = (run: RunWithCases) => (run.verification_comparable ? run.verification_correct / run.verification_comparable : null);

export function useRunViews() {
  const query = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const data = query.data;
  const built = useMemo(() => {
    if (!data) return { views: [] as RunView[], configs: [] as ModelConfig[], byRef: new Map<string, RunView>() };
    const configs = buildConfigs(data, "all");
    const configOf = new Map<string, ModelConfig>();
    for (const config of configs) for (const run of config.runs) configOf.set(run.ref, config);
    const views = data
      .map((run): RunView => {
        const at = runTime(run.run_id);
        return {
          run,
          ref: run.ref,
          at,
          end: at !== null ? at + Math.max(0, run.duration_s ?? 0) * 1000 : null,
          debug: debugOf(run),
          recorded: run.models.DebugAgent.length > 0,
          config: configOf.get(run.ref),
          verifierRate: verifierRate(run),
          missing: Math.max(0, run.planned_cases - run.observed_cases),
        };
      })
      .sort((a, b) => b.run.run_id.localeCompare(a.run.run_id));
    return { views, configs, byRef: new Map(views.map((view) => [view.ref, view])) };
  }, [data]);
  return { ...built, isLoading: query.isLoading, error: query.error };
}

/** Where a run sits among its configuration's repetitions, and their spread. */
export function repetitionOf(view: RunView | undefined): Repetition | undefined {
  const config = view?.config;
  if (!view || !config) return undefined;
  const ordered = config.runRates;
  const rates = ordered.map((r) => r.rate).filter((r): r is number => r !== null);
  return {
    index: ordered.findIndex((r) => r.ref === view.ref) + 1,
    of: ordered.length,
    min: rates.length ? Math.min(...rates) : null,
    max: rates.length ? Math.max(...rates) : null,
  };
}

export const SOURCE_LABEL: Record<RunSource, string> = { canonical: "Canonical", exploratory: "Exploratory", local: "Local" };

export function techniqueShort(technique: string | null): string {
  return technique ? (TECHNIQUE_SHORT[technique] ?? technique) : "unrecorded";
}

export function matchesQuery(view: RunView, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const { run } = view;
  const hay = [
    run.run_id,
    runDate(run.run_id),
    view.debug,
    techniqueLabel(run.technique),
    techniqueShort(run.technique),
    run.source,
    run.status,
    run.ref,
    ...run.models.API,
    ...run.models.Verification,
  ]
    .join(" ")
    .toLowerCase();
  return needle.split(/\s+/).every((token) => hay.includes(token));
}

// ---------------------------------------------------------------- selection

const SELECTION_KEY = "kubellm-compare-selection";

function readSelection(): string[] {
  try {
    const raw = sessionStorage.getItem(SELECTION_KEY);
    const value: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").slice(0, MAX_COMPARE) : [];
  } catch {
    return [];
  }
}

export interface RunSelection {
  selected: string[];
  has: (ref: string) => boolean;
  full: boolean;
  toggle: (ref: string) => void;
  add: (refs: string[]) => void;
  set: (refs: string[]) => void;
  clear: () => void;
}

// The picked runs survive switching options and the trip to Compare and back
// (per tab, per viewer). Losing them is harmless.
export function useRunSelection(): RunSelection {
  const [selected, setSelected] = useState<string[]>(readSelection);
  useEffect(() => {
    try {
      sessionStorage.setItem(SELECTION_KEY, JSON.stringify(selected));
    } catch {
      /* storage unavailable: the selection lasts for this page only */
    }
  }, [selected]);
  const toggle = useCallback(
    (ref: string) => setSelected((current) => (current.includes(ref) ? current.filter((r) => r !== ref) : current.length >= MAX_COMPARE ? current : [...current, ref])),
    [],
  );
  const add = useCallback((refs: string[]) => setSelected((current) => [...current, ...refs.filter((r) => !current.includes(r))].slice(0, MAX_COMPARE)), []);
  const set = useCallback((refs: string[]) => setSelected([...new Set(refs)].slice(0, MAX_COMPARE)), []);
  const clear = useCallback(() => setSelected([]), []);
  return { selected, has: (ref) => selected.includes(ref), full: selected.length >= MAX_COMPARE, toggle, add, set, clear };
}

export const compareHref = (refs: string[]) => `/compare?refs=${refs.join(",")}`;

export function SelectBox({ checked, disabled, onChange, label, className }: { checked: boolean; disabled?: boolean; onChange: () => void; label: string; className?: string }) {
  return (
    <input
      type="checkbox"
      checked={checked}
      disabled={disabled && !checked}
      onChange={onChange}
      aria-label={label}
      title={disabled && !checked ? `Up to ${MAX_COMPARE} runs can be compared` : undefined}
      className={clsx("size-3.5 shrink-0 cursor-pointer accent-accent disabled:cursor-not-allowed disabled:opacity-35", className)}
    />
  );
}

export function AlignmentHint({ runs }: { runs: RunView[] }) {
  if (runs.length < MIN_COMPARE) return <span className="text-[12.5px] text-fg-3">Select at least {MIN_COMPARE} runs</span>;
  const align = alignment(runs.map((v) => v.run));
  return (
    <Tip
      content={
        align.aligned
          ? `Same cases, provider, knowledge model, verifier, and technique. ${align.shared.length} shared cases.`
          : `Differs in ${align.differs.join(", ").toLowerCase()}. ${align.shared.length} of ${align.union.length} cases are shared.`
      }
    >
      <span className="inline-flex min-w-0 items-center gap-2 text-[12.5px] text-fg-2">
        {align.aligned ? (
          <Tag tone="accent" className="shrink-0 whitespace-nowrap">
            Aligned
          </Tag>
        ) : (
          <Tag tone="warn" className="shrink-0 whitespace-nowrap">
            Check alignment
          </Tag>
        )}
        <span className="num truncate">
          {align.shared.length} shared {align.shared.length === 1 ? "case" : "cases"}
          {!align.aligned && <span className="text-fg-3"> · differs: {align.differs.join(", ").toLowerCase()}</span>}
        </span>
      </span>
    </Tip>
  );
}

// Floats at the bottom of the option while runs are picked; Compare opens
// /compare with the refs in the order they were picked (the first is the base).
// The action sits at the left so a floating dock in the bottom-right corner
// never covers it.
export function CompareTray({ selection, byRef }: { selection: RunSelection; byRef: Map<string, RunView> }) {
  const navigate = useNavigate();
  const picked = selection.selected.map((ref) => byRef.get(ref)).filter((v): v is RunView => !!v);
  if (!picked.length) return null;
  return (
    <div className="sticky bottom-3 z-20" role="region" aria-label="Runs selected for comparison">
      <div className="grid gap-2 rounded-lg border border-line-strong bg-surface-2 px-3 py-2.5 shadow-pop">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="flex shrink-0 items-center gap-2">
            <GitCompareArrows className="size-4 text-accent" strokeWidth={1.75} />
            <span className="num text-[12.5px] text-fg-2">
              {picked.length}/{MAX_COMPARE} picked
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Button variant="primary" size="sm" disabled={picked.length < MIN_COMPARE} onClick={() => navigate(compareHref(picked.map((v) => v.ref)))}>
              Compare {picked.length} <ArrowRight className="size-3.5" strokeWidth={2} />
            </Button>
            <Button variant="ghost" size="sm" onClick={selection.clear}>
              Clear
            </Button>
          </div>
          <AlignmentHint runs={picked} />
        </div>
        <ul className="-my-1 flex min-w-0 items-center gap-1.5 overflow-x-auto py-1" aria-label="Picked runs; the first is the base">
          {picked.map((view, index) => (
            <li key={view.ref} className="flex h-7 shrink-0 items-center gap-1.5 rounded-md border border-line bg-surface pr-0.5 pl-2 text-[12px]">
              <span className={clsx("num text-[11px]", index === 0 ? "text-accent" : "text-fg-3")} title={index === 0 ? "Base run" : undefined}>
                {index === 0 ? "Base" : index + 1}
              </span>
              <LabLogo lab={labOf(view.debug)} size={12} />
              <span className="ident max-w-[132px] truncate text-fg">{displayModel(view.debug)}</span>
              <span className="whitespace-nowrap text-fg-3">{runDate(view.run.run_id)}</span>
              <button
                type="button"
                onClick={() => selection.toggle(view.ref)}
                aria-label={`Remove ${view.debug} run ${view.run.run_id}`}
                className="grid size-6 cursor-pointer place-items-center rounded text-fg-3 hover:bg-surface-3 hover:text-fg"
              >
                <X className="size-3.5" strokeWidth={1.75} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// Callback ref so the observer attaches once the measured element mounts.
export function useWidth() {
  const [el, setEl] = useState<HTMLElement | null>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, [el]);
  return [setEl, width] as const;
}

// ---------------------------------------------------------------- labels

export function RunModel({ view, link = true, size = 13, className }: { view: RunView; link?: boolean; size?: number; className?: string }) {
  const inner = (
    <>
      <LabLogo lab={labOf(view.debug)} size={size} />
      <span className={clsx("ident truncate", view.recorded ? "text-fg" : "text-fg-3")} title={view.debug}>
        {view.recorded ? displayModel(view.debug) : "unrecorded"}
      </span>
    </>
  );
  const cls = clsx("inline-flex min-w-0 max-w-full items-center gap-2", className);
  if (!view.config || !view.recorded) return <span className={cls}>{inner}</span>;
  return (
    <ModelCard config={view.config} side="right">
      {link ? (
        <Link to={`/models/${view.config.slug}`} className={clsx(cls, "hover:[&>span:last-child]:underline")}>
          {inner}
        </Link>
      ) : (
        <span tabIndex={0} className={cls}>
          {inner}
        </span>
      )}
    </ModelCard>
  );
}

export function IncompleteTag({ run }: { run: RunWithCases }) {
  const missing = run.planned_cases - run.observed_cases;
  return (
    <Tip
      content={`${run.ground_truth_unavailable} recorded ${run.ground_truth_unavailable === 1 ? "attempt lacks" : "attempts lack"} a Ground Truth outcome${missing > 0 ? `; ${missing} planned ${missing === 1 ? "case was" : "cases were"} not recorded` : ""}. Nothing is inferred.`}
    >
      <span tabIndex={0} className="inline-flex">
        <Tag tone="warn">Incomplete</Tag>
      </span>
    </Tip>
  );
}

export function RateBar({ rate, width = 56, active }: { rate: number | null; width?: number; active?: boolean }) {
  return (
    <span className="relative inline-block h-1.5 shrink-0 overflow-hidden rounded-full bg-track align-middle" style={{ width }}>
      {rate === null ? (
        <span className="hatch absolute inset-0 opacity-70" />
      ) : (
        <span className={clsx("absolute inset-y-0 left-0 rounded-full", active ? "bg-accent" : "bg-fg-2")} style={{ width: `${rate * 100}%` }} />
      )}
    </span>
  );
}

export function gtTip(run: RunWithCases) {
  return run.ground_truth_rate === null
    ? `No attempt has a known Ground Truth outcome${run.ground_truth_unavailable ? ` (${run.ground_truth_unavailable} unknown)` : ""}.`
    : `${run.ground_truth_passed} of ${run.ground_truth_known} known attempts passed Ground Truth${run.ground_truth_unavailable ? `; ${run.ground_truth_unavailable} unknown, excluded from the rate` : ""}.`;
}

// ---------------------------------------------------------------- controls

export function SearchField({ value, onChange, placeholder, inputRef, className }: { value: string; onChange: (next: string) => void; placeholder: string; inputRef?: Ref<HTMLInputElement>; className?: string }) {
  return (
    <label className={clsx("flex h-8 min-w-0 items-center gap-2 rounded-md border border-line bg-surface px-2.5 text-[13px] text-fg-3 focus-within:border-accent-line", className)}>
      <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3"
      />
      {value && (
        <button type="button" onClick={() => onChange("")} aria-label="Clear search" className="grid size-5 cursor-pointer place-items-center rounded text-fg-3 hover:text-fg">
          <X className="size-3.5" strokeWidth={1.75} />
        </button>
      )}
    </label>
  );
}

export interface MenuOption<T extends string> {
  value: T;
  label: ReactNode;
  count: number;
}

export function FilterMenu<T extends string>({ label, options, selected, onChange }: { label: string; options: MenuOption<T>[]; selected: Set<T>; onChange: (next: Set<T>) => void }) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className={clsx(
            "inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 rounded-md border px-2.5 text-[12.5px] transition-colors",
            selected.size ? "border-accent-line bg-accent-soft text-fg" : "border-line bg-surface text-fg-2 hover:border-line-strong hover:text-fg",
          )}
        >
          {label}
          {selected.size > 0 && <span className="num rounded-[3px] bg-accent px-1 text-[10.5px] leading-4 text-accent-ink">{selected.size}</span>}
          <ChevronDown className="size-3.5 text-fg-3" strokeWidth={1.75} />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="start" sideOffset={6} collisionPadding={12} className="z-50 max-h-[min(420px,var(--radix-dropdown-menu-content-available-height))] min-w-[220px] overflow-y-auto rounded-lg bg-surface-2 p-1 shadow-pop">
          <DropdownMenu.Label className="label px-2 pt-1.5 pb-1 !text-[10px]">{label}</DropdownMenu.Label>
          {options.map((option) => (
            <DropdownMenu.CheckboxItem
              key={option.value}
              checked={selected.has(option.value)}
              onSelect={(event) => event.preventDefault()}
              onCheckedChange={(on) => {
                const next = new Set(selected);
                if (on) next.add(option.value);
                else next.delete(option.value);
                onChange(next);
              }}
              className="flex h-8 cursor-pointer items-center gap-2 rounded-md px-2 text-[12.5px] text-fg-2 outline-none select-none data-[highlighted]:bg-surface-3 data-[highlighted]:text-fg data-[state=checked]:text-fg"
            >
              <span className="grid size-3.5 shrink-0 place-items-center rounded-[3px] border border-line-strong">
                <DropdownMenu.ItemIndicator>
                  <Check className="size-3 text-accent" strokeWidth={2.5} />
                </DropdownMenu.ItemIndicator>
              </span>
              <span className="flex min-w-0 items-center gap-2">{option.label}</span>
              <span className="num ml-auto pl-3 text-[11.5px] text-fg-3">{option.count}</span>
            </DropdownMenu.CheckboxItem>
          ))}
          {selected.size > 0 && (
            <>
              <DropdownMenu.Separator className="my-1 h-px bg-line" />
              <DropdownMenu.Item onSelect={() => onChange(new Set())} className="flex h-8 cursor-pointer items-center rounded-md px-2 text-[12.5px] text-fg-3 outline-none data-[highlighted]:bg-surface-3 data-[highlighted]:text-fg">
                Clear {label.toLowerCase()} filter
              </DropdownMenu.Item>
            </>
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export function countBy<T>(items: T[], key: (item: T) => string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(key(item), (counts.get(key(item)) ?? 0) + 1);
  return counts;
}

export function ModelOptionLabel({ model }: { model: string }) {
  return (
    <>
      <LabLogo lab={labOf(model)} size={13} />
      <span className="ident truncate">{model === "unrecorded" ? "unrecorded" : displayModel(model)}</span>
    </>
  );
}

export function EmptyRow({ children }: { children: ReactNode }) {
  return <div className="px-4 py-10 text-center text-[13px] text-fg-3">{children}</div>;
}

