// The Compare frame every option shares: ?refs= parsing (2–8 distinct runs, as
// POST /api/compare requires), a sensible default, the run picker, run
// markers, and the alignment panel with the backend's caution verbatim.
import clsx from "clsx";
import { Check, ChevronDown, Info, Layers, X } from "lucide-react";
import { Dialog } from "radix-ui";
import { useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import type { RunSource } from "@/api/types";
import { displayModel } from "@/components/charts";
import { LabLogo } from "@/components/ModelCard";
import { Button, Segmented, Tag, Tip } from "@/components/ui";
import { labOf } from "@/data/models";
import { rankConfigs, type ModelConfig } from "@/lib/explore";
import { count, pct, runDate } from "@/lib/format";
import {
  matchesQuery,
  RunModel,
  SearchField,
  SOURCE_LABEL,
  techniqueShort,
  IncompleteTag,
  repetitionOf,
  useRunViews,
  type RunView,
} from "../runs/shared";
import { alignment, CAUTION, MAX_COMPARE, MIN_COMPARE, sharedCases, type Alignment, type Dimension } from "./model";

export type Scope = "shared" | "all";

function defaultRefs(configs: ModelConfig[], views: RunView[]): string[] {
  const canonical = rankConfigs(configs.filter((c) => c.source === "canonical"));
  const refs = canonical.slice(0, 3).map((c) => c.runs[0]?.ref).filter((ref): ref is string => !!ref);
  return refs.length >= MIN_COMPARE ? refs : views.slice(0, MIN_COMPARE).map((v) => v.ref);
}

export interface CompareState {
  isLoading: boolean;
  error: unknown;
  all: RunView[];
  runs: RunView[];
  align: Alignment;
  /** Cases the metrics use: shared cases, or each run's own recorded cases. */
  scope: Scope;
  setScope: (scope: Scope) => void;
  casesFor: (view: RunView) => string[] | null;
  notice: "default" | "invalid" | "trimmed" | null;
  setRefs: (refs: string[]) => void;
  makeBase: (ref: string) => void;
  remove: (ref: string) => void;
}

export function useCompare(): CompareState {
  const { views, configs, byRef, isLoading, error } = useRunViews();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [scope, setScope] = useState<Scope>("shared");
  const raw = params.get("refs");

  const resolved = useMemo(() => {
    const requested = raw ? raw.split(",").map((s) => s.trim()).filter(Boolean) : [];
    const distinct = [...new Set(requested)];
    const found = distinct.filter((ref) => byRef.has(ref));
    const valid = found.slice(0, MAX_COMPARE);
    const fallback = valid.length < MIN_COMPARE;
    const refs = fallback ? defaultRefs(configs, views) : valid;
    const notice: CompareState["notice"] = !raw ? "default" : fallback ? "invalid" : requested.length !== valid.length ? "trimmed" : null;
    return { refs, notice };
  }, [raw, byRef, configs, views]);

  const runs = useMemo(() => resolved.refs.map((ref) => byRef.get(ref)).filter((v): v is RunView => !!v), [resolved.refs, byRef]);
  const align = useMemo(() => alignment(runs.map((v) => v.run), runs.map(repetitionOf)), [runs]);

  // Commas stay literal so a comparison link stays readable when shared.
  const setRefs = (next: string[]) => {
    const rest = new URLSearchParams(params);
    rest.delete("refs");
    const head = rest.toString();
    navigate({ pathname, search: `?${head ? `${head}&` : ""}refs=${[...new Set(next)].slice(0, MAX_COMPARE).join(",")}` });
  };
  const current = runs.map((v) => v.ref);

  return {
    isLoading,
    error,
    all: views,
    runs,
    align,
    scope,
    setScope,
    casesFor: () => (scope === "shared" ? align.shared : null),
    notice: resolved.notice,
    setRefs,
    makeBase: (ref) => setRefs([ref, ...current.filter((r) => r !== ref)]),
    remove: (ref) => current.length > MIN_COMPARE && setRefs(current.filter((r) => r !== ref)),
  };
}

// ---------------------------------------------------------------- identity

export function RunMarker({ index, className, size = 18 }: { index: number; className?: string; size?: number }) {
  return (
    <span
      aria-hidden
      className={clsx("inline-grid shrink-0 place-items-center rounded-[4px] font-mono text-[10.5px] leading-none font-medium", index === 0 ? "bg-accent text-accent-ink" : "bg-surface-3 text-fg-2", className)}
      style={{ width: size, height: size }}
    >
      {index + 1}
    </span>
  );
}

export const runName = (view: RunView, index: number) => `${index === 0 ? "Base" : `Run ${index + 1}`}: ${view.debug}, ${runDate(view.run.run_id)}`;

/** Full identity of one compared run: marker, model card, date, settings. */
export function RunHead({ view, index, state, compact }: { view: RunView; index: number; state: CompareState; compact?: boolean }) {
  const { run } = view;
  return (
    <div className="grid min-w-0 gap-1">
      <div className="flex min-w-0 items-center gap-2">
        <RunMarker index={index} />
        <RunModel view={view} className="text-[12.5px] font-medium" />
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 pl-[26px] text-[11.5px] text-fg-3">
        <Link to={`/runs/${view.ref}`} className="text-fg-2 hover:text-fg hover:underline hover:decoration-line-strong hover:underline-offset-2">
          {runDate(run.run_id)}
        </Link>
        <span aria-hidden>·</span>
        <span>{techniqueShort(run.technique)}</span>
        {!compact && (
          <>
            <span aria-hidden>·</span>
            <span>{SOURCE_LABEL[run.source].toLowerCase()}</span>
          </>
        )}
        {run.status === "incomplete" && <IncompleteTag run={run} />}
      </div>
      <div className="flex items-center gap-1 pl-[22px]">
        {index === 0 ? (
          <span className="label px-1 !text-[9.5px] !text-accent">Base</span>
        ) : (
          <button type="button" onClick={() => state.makeBase(view.ref)} className="h-6 cursor-pointer rounded px-1 text-[11.5px] text-fg-3 hover:bg-surface-2 hover:text-fg">
            Make base
          </button>
        )}
        {state.runs.length > MIN_COMPARE && (
          <button
            type="button"
            onClick={() => state.remove(view.ref)}
            aria-label={`Remove ${runName(view, index)} from the comparison`}
            className="grid size-6 cursor-pointer place-items-center rounded text-fg-3 hover:bg-surface-2 hover:text-fg"
          >
            <X className="size-3.5" strokeWidth={1.75} />
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- picker

function PickerRow({ view, order, disabled, onToggle }: { view: RunView; order: number; disabled: boolean; onToggle: () => void }) {
  const { run } = view;
  const on = order >= 0;
  return (
    <li>
      <label
        className={clsx(
          "grid cursor-pointer grid-cols-[18px_22px_minmax(0,1fr)_auto] items-center gap-x-2.5 px-4 py-2 text-[12.5px] transition-colors sm:grid-cols-[18px_22px_minmax(0,1fr)_150px_110px_64px]",
          on ? "bg-accent-soft" : "hover:bg-surface-3/50",
          disabled && !on && "cursor-not-allowed opacity-50",
        )}
      >
        <input type="checkbox" checked={on} disabled={disabled && !on} onChange={onToggle} className="size-3.5 cursor-pointer accent-accent disabled:cursor-not-allowed" />
        {on ? <RunMarker index={order} /> : <span />}
        <span className="grid min-w-0 gap-0.5">
          <span className="flex min-w-0 items-center gap-2">
            <LabLogo lab={labOf(view.debug)} size={13} />
            <span className={clsx("ident truncate", view.recorded ? "text-fg" : "text-fg-3")}>{view.recorded ? displayModel(view.debug) : "unrecorded"}</span>
          </span>
          <span className="truncate pl-[21px] text-[11.5px] text-fg-3 sm:hidden">
            {runDate(run.run_id)} · {techniqueShort(run.technique)}
          </span>
        </span>
        <span className="hidden truncate text-fg-2 sm:block">{runDate(run.run_id)}</span>
        <span className="hidden truncate text-fg-3 sm:block">
          {techniqueShort(run.technique)} · {run.source === "canonical" ? "canon" : run.source === "exploratory" ? "expl" : "local"}
        </span>
        <span className="num text-right">
          <span className="text-fg">{pct(run.ground_truth_rate, 0)}</span>
          <span className="block text-[11px] text-fg-3">{run.observed_cases} cases</span>
        </span>
      </label>
    </li>
  );
}

export function RunPicker({ state, trigger }: { state: CompareState; trigger?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [source, setSource] = useState<"all" | RunSource>("all");
  const searchRef = useRef<HTMLInputElement>(null);
  const onOpen = (next: boolean) => {
    if (next) {
      setDraft(state.runs.map((v) => v.ref));
      setQuery("");
    }
    setOpen(next);
  };
  const list = state.all.filter((v) => (source === "all" || v.run.source === source) && matchesQuery(v, query));
  const toggle = (ref: string) => setDraft((cur) => (cur.includes(ref) ? cur.filter((r) => r !== ref) : cur.length >= MAX_COMPARE ? cur : [...cur, ref]));
  const draftViews = draft.map((ref) => state.all.find((v) => v.ref === ref)).filter((v): v is RunView => !!v);
  const draftShared = sharedCases(draftViews.map((v) => v.run)).length;

  return (
    <Dialog.Root open={open} onOpenChange={onOpen}>
      <Dialog.Trigger asChild>
        {trigger ?? (
          <Button size="sm">
            <Layers className="size-3.5" strokeWidth={1.75} /> Change runs
          </Button>
        )}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
        <Dialog.Content
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            searchRef.current?.focus();
          }}
          className="fixed top-1/2 left-1/2 z-50 flex h-[min(680px,calc(100dvh-32px))] w-[min(760px,calc(100vw-24px))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg border border-line bg-surface-2 shadow-pop">
          <div className="flex items-start gap-3 border-b border-line px-4 py-3.5">
            <div className="min-w-0">
              <Dialog.Title className="text-[15px] font-medium">Choose runs to compare</Dialog.Title>
              <Dialog.Description className="mt-0.5 text-[12.5px] text-fg-3">
                Two to eight distinct runs. The first one ticked is the base; the rest are compared against it.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button type="button" aria-label="Close" className="ml-auto grid size-8 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-3 hover:text-fg">
                <X className="size-4" strokeWidth={1.75} />
              </button>
            </Dialog.Close>
          </div>
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5">
            <SearchField value={query} onChange={setQuery} placeholder="Search runs" inputRef={searchRef} className="w-full sm:w-64" />
            <Segmented
              label="Source"
              value={source}
              onChange={setSource}
              options={[{ value: "all", label: "All" }, { value: "canonical", label: "Canonical" }, { value: "exploratory", label: "Exploratory" }]}
            />
            <span className="num ml-auto text-[12px] text-fg-3">{count(list.length)} runs</span>
          </div>
          {draftViews.length > 0 && (
            <ul className="flex items-center gap-1.5 overflow-x-auto border-b border-line px-4 py-2" aria-label="Selected runs in comparison order">
              {draftViews.map((view, index) => (
                <li key={view.ref} className="flex h-7 shrink-0 items-center gap-1.5 rounded-md border border-line bg-surface pr-0.5 pl-1.5 text-[12px]">
                  <RunMarker index={index} size={16} className="!text-[9.5px]" />
                  <LabLogo lab={labOf(view.debug)} size={12} />
                  <span className="ident max-w-[120px] truncate text-fg">{view.recorded ? displayModel(view.debug) : "unrecorded"}</span>
                  <span className="whitespace-nowrap text-fg-3">{runDate(view.run.run_id)}</span>
                  <button
                    type="button"
                    onClick={() => toggle(view.ref)}
                    aria-label={`Remove ${view.debug} run ${view.run.run_id}`}
                    className="grid size-6 cursor-pointer place-items-center rounded text-fg-3 hover:bg-surface-3 hover:text-fg"
                  >
                    <X className="size-3.5" strokeWidth={1.75} />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <ul className="min-h-0 flex-1 divide-y divide-line overflow-y-auto">
            {list.map((view) => (
              <PickerRow key={view.ref} view={view} order={draft.indexOf(view.ref)} disabled={draft.length >= MAX_COMPARE} onToggle={() => toggle(view.ref)} />
            ))}
            {list.length === 0 && <li className="px-4 py-10 text-center text-[13px] text-fg-3">No run matches.</li>}
          </ul>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-line px-4 py-3">
            <span className="num text-[12.5px] text-fg-2">
              {draft.length}/{MAX_COMPARE} selected
              {draft.length >= MIN_COMPARE && <span className="text-fg-3"> · {draftShared} shared {draftShared === 1 ? "case" : "cases"}</span>}
            </span>
            {draft.length > 0 && (
              <button type="button" onClick={() => setDraft([])} className="h-7 cursor-pointer rounded-md px-2 text-[12.5px] text-fg-3 hover:bg-surface-3 hover:text-fg">
                Clear
              </button>
            )}
            <div className="ml-auto flex items-center gap-2">
              <Dialog.Close asChild>
                <Button size="sm" variant="ghost">
                  Cancel
                </Button>
              </Dialog.Close>
              <Button
                size="sm"
                variant="primary"
                disabled={draft.length < MIN_COMPARE}
                onClick={() => {
                  state.setRefs(draft);
                  setOpen(false);
                }}
              >
                Compare {draft.length} runs
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ---------------------------------------------------------------- notices

export function CompareNotice({ state }: { state: CompareState }) {
  if (!state.notice) return null;
  const text = {
    default: "No runs were named, so this shows the latest canonical run of the three highest-ranked models. Change runs to pick your own.",
    invalid: `The link named fewer than ${MIN_COMPARE} recorded runs, so this shows the default: the latest canonical run of the three highest-ranked models.`,
    trimmed: `The link named runs that are duplicated, not in the recorded data, or beyond the limit of ${MAX_COMPARE}; they were left out.`,
  }[state.notice];
  return (
    <p className={clsx("flex items-start gap-2 text-[12.5px]", state.notice === "default" ? "text-fg-3" : "text-warn")}>
      <Info className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.75} />
      {text}
    </p>
  );
}

export function ScopeToggle({ state }: { state: CompareState }) {
  return (
    <Segmented
      label="Cases used for metrics"
      value={state.scope}
      onChange={state.setScope}
      options={[
        { value: "shared", label: <>Shared cases <span className="num text-fg-3">{state.align.shared.length}</span></>, hint: "Only the cases every run planned" },
        { value: "all", label: "All recorded", hint: "Each run's own recorded cases; coverage differences can drive the numbers" },
      ]}
    />
  );
}

// ---------------------------------------------------------------- alignment

function DimensionValues({ dim }: { dim: Dimension }) {
  if (dim.same && dim.key !== "repetition") return <span className="ident text-fg">{dim.values[0]}</span>;
  const groups = new Map<string, number[]>();
  dim.values.forEach((value, index) => groups.set(value, [...(groups.get(value) ?? []), index]));
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-1">
      {[...groups.entries()].map(([value, indexes]) => (
        <span key={value} className="inline-flex min-w-0 items-center gap-1.5">
          <span className="inline-flex gap-0.5">
            {indexes.map((i) => (
              <RunMarker key={i} index={i} size={15} className="!text-[9.5px]" />
            ))}
          </span>
          <span className="ident truncate text-fg">{value}</span>
        </span>
      ))}
    </span>
  );
}

function DimensionState({ dim }: { dim: Dimension }) {
  if (dim.key === "repetition") return <span className="text-fg-3">One run each</span>;
  if (dim.info) return <span className="text-fg-3">{dim.same ? "Same" : "Varies"}</span>;
  return dim.same ? (
    <span className="inline-flex items-center gap-1 text-fg-2">
      <Check className="size-3.5" strokeWidth={2} /> Same
    </span>
  ) : (
    <span className="font-medium text-warn">Differs</span>
  );
}

export function AlignmentPanel({ state, defaultOpen, compact, className }: { state: CompareState; defaultOpen?: boolean; compact?: boolean; className?: string }) {
  const { align } = state;
  const [open, setOpen] = useState(defaultOpen ?? !align.aligned);
  return (
    <section className={clsx("min-w-0 rounded-lg border border-line bg-surface", className)} aria-label="Alignment">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        {align.aligned ? <Tag tone="accent">Aligned</Tag> : <Tag tone="warn">Check alignment</Tag>}
        <span className="num text-[13px] text-fg">
          {align.shared.length} shared {align.shared.length === 1 ? "case" : "cases"}
          <span className="text-fg-3"> of {align.union.length}</span>
        </span>
        <span className="min-w-0 text-[12.5px] text-fg-3">
          {align.aligned ? "Same cases, provider, knowledge model, verifier, and technique." : `Differs in ${align.differs.join(", ").toLowerCase()}.`}
        </span>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="ml-auto inline-flex h-7 cursor-pointer items-center gap-1 rounded-md px-2 text-[12.5px] text-fg-3 hover:bg-surface-2 hover:text-fg"
        >
          {open ? "Hide details" : "Details"}
          <ChevronDown className={clsx("size-3.5 transition-transform motion-reduce:transition-none", open && "rotate-180")} strokeWidth={1.75} />
        </button>
      </div>
      {open && (
        <dl className="grid border-t border-line text-[12.5px]">
          {align.dimensions.map((dim) => (
            <div
              key={dim.key}
              className={clsx(
                "grid gap-x-4 gap-y-1 border-b border-line px-4 py-2 last:border-b-0",
                compact ? "grid-cols-[minmax(0,1fr)_auto]" : "grid-cols-[minmax(0,1fr)_auto] sm:grid-cols-[140px_96px_minmax(0,1fr)]",
              )}
            >
              <dt className="text-fg-2">{dim.label}</dt>
              <dd className="text-right sm:text-left">
                <DimensionState dim={dim} />
              </dd>
              <dd className={clsx("col-span-2 grid min-w-0 gap-0.5", !compact && "sm:col-span-1")}>
                <DimensionValues dim={dim} />
                {dim.note && <span className="text-[11.5px] text-fg-3">{dim.note}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p className="flex items-start gap-2 border-t border-line px-4 py-2.5 text-[12.5px] text-fg-2">
        <Info className="mt-0.5 size-3.5 shrink-0 text-fg-3" strokeWidth={1.75} />
        <span>{CAUTION}</span>
      </p>
    </section>
  );
}

// ---------------------------------------------------------------- deltas

export type Better = "higher" | "lower";

/** Neutral delta for signals that are not Ground Truth outcomes: arrow plus a word, no outcome color. */
export function NeutralDelta({ base, value, better, kind, words }: { base: number | null; value: number | null; better: Better; kind: "pp" | "ratio"; words: [string, string] }) {
  if (base === null || value === null) return <span className="text-fg-3">—</span>;
  const diff = value - base;
  const rel = kind === "ratio" ? (base === 0 ? null : diff / base) : diff;
  if (rel === null) return <span className="text-fg-3">—</span>;
  if (Math.abs(rel) < (kind === "pp" ? 0.0005 : 0.005)) return <span className="text-fg-3">No change</span>;
  const improves = better === "higher" ? diff > 0 : diff < 0;
  const Arrow = diff > 0 ? "↑" : "↓";
  const amount = kind === "pp" ? `${diff > 0 ? "+" : "−"}${Math.abs(diff * 100).toFixed(1)} pp` : `${diff > 0 ? "+" : "−"}${Math.abs(rel * 100).toFixed(0)}%`;
  return (
    <span className="num inline-flex items-center gap-1 whitespace-nowrap text-fg-2">
      <span aria-hidden>{Arrow}</span>
      {amount}
      <span className="text-fg-3">{improves ? words[0] : words[1]}</span>
    </span>
  );
}

/** Ground Truth delta: green or red, always with an arrow and a number. */
export function OutcomeDelta({ base, value }: { base: number | null; value: number | null }) {
  if (base === null || value === null) return <span className="text-fg-3">—</span>;
  const diff = value - base;
  if (Math.abs(diff) < 0.0005) return <span className="num text-fg-3">± 0 pp</span>;
  return (
    <span className={clsx("num inline-flex items-center gap-1 font-medium whitespace-nowrap", diff > 0 ? "text-good" : "text-bad")}>
      <span aria-hidden>{diff > 0 ? "↑" : "↓"}</span>
      {diff > 0 ? "+" : "−"}
      {Math.abs(diff * 100).toFixed(1)} pp
    </span>
  );
}

export function FlipCounts({ improved, regressed, uncomparable }: { improved: number; regressed: number; uncomparable: number }) {
  return (
    <span className="num inline-flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[12px]">
      <span className={improved ? "text-good" : "text-fg-3"} title={`${improved} cases failed in the base and passed here`}>
        ↑ {improved} improved
      </span>
      <span className={regressed ? "text-bad" : "text-fg-3"} title={`${regressed} cases passed in the base and failed here`}>
        ↓ {regressed} regressed
      </span>
      {uncomparable > 0 && (
        <Tip content="Cases where either run has no known Ground Truth outcome or no recorded attempt. They cannot be compared.">
          <span tabIndex={0} className="text-warn">
            {uncomparable} not comparable
          </span>
        </Tip>
      )}
    </span>
  );
}

export function CompareLoading() {
  return <div className="h-[560px] animate-pulse rounded-lg bg-surface" />;
}
