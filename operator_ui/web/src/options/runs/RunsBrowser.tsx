// Runs: the experiments table, with the timeline as a second view of the same
// runs. Search, source, filters, sort, the zoom window, and the compare
// selection live here, so switching views keeps all of them. The view is in
// the URL (?view=timeline) so it can be linked and survives a refresh.
import { ChartGantt, Rows3, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import type { RunSource, Technique } from "@/api/types";
import { ErrorState, LoadingState } from "@/components/states";
import { Segmented } from "@/components/ui";
import { techniqueLabel } from "@/lib/explore";
import { count } from "@/lib/format";
import { DEFAULT_SORT, nextSort, RunsSummary, RunsTable, sortRuns, type SortState } from "./ExperimentsTable";
import { CompareTray, countBy, FilterMenu, matchesQuery, ModelOptionLabel, SearchField, SOURCE_LABEL, useRunSelection, useRunViews, type RunView } from "./shared";
import { RunsTimeline, type Range } from "./Timeline";

type View = "table" | "timeline";
type Status = "recorded" | "incomplete";
type Facet = "source" | "technique" | "model" | "status";

const PAGE = 40;

export default function RunsBrowser() {
  const { views, byRef, isLoading, error } = useRunViews();
  const selection = useRunSelection();
  const [params, setParams] = useSearchParams();
  const view: View = params.get("view") === "timeline" ? "timeline" : "table";
  const [query, setQuery] = useState("");
  const [source, setSource] = useState<"all" | RunSource>("all");
  const [techniques, setTechniques] = useState<Set<string>>(new Set());
  const [models, setModels] = useState<Set<string>>(new Set());
  const [statuses, setStatuses] = useState<Set<Status>>(new Set());
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [limit, setLimit] = useState(PAGE);
  const [win, setWin] = useState<Range | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // "/" jumps to search, as in most run browsers.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (event.key !== "/" || event.metaKey || event.ctrlKey || target?.closest("input, textarea, [contenteditable=true]")) return;
      event.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const setView = (next: View) =>
    setParams(
      (current) => {
        const out = new URLSearchParams(current);
        if (next === "table") out.delete("view");
        else out.set("view", next);
        return out;
      },
      { replace: true },
    );

  const passes = (run: RunView, except?: Facet) =>
    matchesQuery(run, query) &&
    (except === "source" || source === "all" || run.run.source === source) &&
    (except === "technique" || !techniques.size || techniques.has(run.run.technique ?? "unrecorded")) &&
    (except === "model" || !models.size || models.has(run.debug)) &&
    (except === "status" || !statuses.size || statuses.has(run.run.status));

  const filtered = useMemo(() => views.filter((v) => passes(v)), [views, query, source, techniques, models, statuses]);
  const rows = useMemo(() => sortRuns(filtered, sort), [filtered, sort]);

  if (isLoading) return <LoadingState label="Reading recorded runs" />;
  if (error) return <ErrorState error={error} />;

  const sources = countBy(views.filter((v) => passes(v, "source")), (v) => v.run.source);
  const techniqueCounts = countBy(views.filter((v) => passes(v, "technique")), (v) => v.run.technique ?? "unrecorded");
  const modelCounts = countBy(views.filter((v) => passes(v, "model")), (v) => v.debug);
  const statusCounts = countBy(views.filter((v) => passes(v, "status")), (v) => v.run.status);
  const allTechniques = [...new Set(views.map((v) => v.run.technique ?? "unrecorded"))].sort();
  const allModels = [...new Set(views.map((v) => v.debug))].sort((a, b) => (a === "unrecorded" ? 1 : b === "unrecorded" ? -1 : a.localeCompare(b)));

  const chips: { label: string; clear: () => void }[] = [
    ...[...techniques].map((t) => ({ label: `Technique: ${t === "unrecorded" ? "unrecorded" : techniqueLabel(t as Technique)}`, clear: () => setTechniques((s) => new Set([...s].filter((x) => x !== t))) })),
    ...[...models].map((m) => ({ label: `Model: ${m}`, clear: () => setModels((s) => new Set([...s].filter((x) => x !== m))) })),
    ...[...statuses].map((s) => ({ label: `Status: ${s}`, clear: () => setStatuses((cur) => new Set([...cur].filter((x) => x !== s))) })),
  ];
  const clearAll = () => {
    setQuery("");
    setSource("all");
    setTechniques(new Set());
    setModels(new Set());
    setStatuses(new Set());
    setWin(null);
  };

  return (
    <div className="grid gap-4">
      <div className="border-y border-line py-4">
        <RunsSummary views={filtered} total={views.length} />
      </div>

      <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="Recorded runs">
        <div className="grid gap-2.5 border-b border-line px-3 py-3 sm:px-4">
          <div className="flex flex-wrap items-center gap-2">
            <SearchField value={query} onChange={setQuery} placeholder="Search runs, models, IDs" inputRef={searchRef} className="w-full sm:w-72" />
            <Segmented
              label="Source"
              value={source}
              onChange={(next) => {
                setSource(next);
                // A new source has a different time extent; start the timeline from all time.
                setWin(null);
              }}
              options={[
                { value: "all", label: <>All <span className="num text-fg-3">{[...sources.values()].reduce((a, b) => a + b, 0)}</span></> },
                ...(["canonical", "exploratory", "local"] as RunSource[])
                  .filter((s) => views.some((v) => v.run.source === s))
                  .map((s) => ({ value: s, label: <>{SOURCE_LABEL[s]} <span className="num text-fg-3">{sources.get(s) ?? 0}</span></> })),
              ]}
            />
            <FilterMenu
              label="Technique"
              selected={techniques}
              onChange={setTechniques}
              options={allTechniques.map((t) => ({ value: t, label: t === "unrecorded" ? "Unrecorded" : techniqueLabel(t as Technique), count: techniqueCounts.get(t) ?? 0 }))}
            />
            <FilterMenu label="Model" selected={models} onChange={setModels} options={allModels.map((m) => ({ value: m, label: <ModelOptionLabel model={m} />, count: modelCounts.get(m) ?? 0 }))} />
            <FilterMenu
              label="Status"
              selected={statuses}
              onChange={setStatuses}
              options={[
                { value: "recorded" as Status, label: "Recorded", count: statusCounts.get("recorded") ?? 0 },
                { value: "incomplete" as Status, label: <span className="text-warn">Incomplete</span>, count: statusCounts.get("incomplete") ?? 0 },
              ]}
            />
            {/* The summary above shows the filtered count; this announces it. */}
            <span className="sr-only" aria-live="polite">
              {count(rows.length)} of {count(views.length)} runs match
            </span>
            <div className="ml-auto">
              <Segmented
                label="View"
                value={view}
                onChange={setView}
                options={[
                  { value: "table", label: <><Rows3 className="size-3.5" strokeWidth={1.75} aria-hidden /> Table</>, hint: "One sortable row per run" },
                  { value: "timeline", label: <><ChartGantt className="size-3.5" strokeWidth={1.75} aria-hidden /> Timeline</>, hint: "Runs over time, one lane per debug model" },
                ]}
              />
            </div>
          </div>
          {(chips.length > 0 || query || source !== "all") && (
            <div className="flex flex-wrap items-center gap-1.5">
              {chips.map((chip) => (
                <span key={chip.label} className="inline-flex h-6 items-center gap-1 rounded-md border border-line bg-surface-2 pr-0.5 pl-2 text-[12px] text-fg-2">
                  {chip.label}
                  <button type="button" onClick={chip.clear} aria-label={`Remove filter ${chip.label}`} className="grid size-5 cursor-pointer place-items-center rounded text-fg-3 hover:text-fg">
                    <X className="size-3" strokeWidth={2} />
                  </button>
                </span>
              ))}
              <button type="button" onClick={clearAll} className="h-6 cursor-pointer rounded-md px-2 text-[12px] text-fg-3 hover:bg-surface-2 hover:text-fg">
                Clear all
              </button>
            </div>
          )}
        </div>

        {view === "table" ? (
          <RunsTable
            rows={rows}
            selection={selection}
            sort={sort}
            onSort={(key) => setSort((current) => nextSort(current, key))}
            limit={limit}
            onShowAll={() => setLimit(rows.length)}
            onClearFilters={clearAll}
          />
        ) : (
          <RunsTimeline views={filtered} selection={selection} win={win} onWindow={setWin} onClearFilters={clearAll} />
        )}
      </section>

      <CompareTray selection={selection} byRef={byRef} />
    </div>
  );
}
