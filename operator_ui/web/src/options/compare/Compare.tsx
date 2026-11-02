import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import { useEffect, useRef } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { ErrorState } from "@/components/states";
import { RunModel } from "../runs/shared";
import { runDate } from "@/lib/format";
import { CaseMatrix, caseCounts, useCaseLines, type CaseFilter } from "./CaseDiff";
import { FlipLists, MetricTable } from "./MetricRows";
import { caseDiff, sideStats } from "./model";
import { AlignmentPanel, CompareLoading, CompareNotice, RunMarker, RunPicker, ScopeToggle, useCompare } from "./shared";

// The Compare page: metric rows against a base run, then the cases behind
// them. The case section shows Ground Truth flips per run and expands into the
// full case diff matrix; ?cases=<filter> keeps it open in a shared link.

const FILTERS: CaseFilter[] = ["all", "differ", "regressed", "improved"];

/** Replaces only the cases parameter, keeping the rest of the query (and literal commas in refs) as written. */
function withCases(search: string, value: CaseFilter | null) {
  const parts = search
    .replace(/^\?/, "")
    .split("&")
    .filter((part) => part && !part.startsWith("cases="));
  if (value) parts.push(`cases=${value}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

export default function Compare() {
  const state = useCompare();
  const lines = useCaseLines(state);
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const sectionRef = useRef<HTMLElement>(null);
  const revealPending = useRef(false);

  const raw = params.get("cases");
  const filter: CaseFilter | null = raw === null ? null : FILTERS.includes(raw as CaseFilter) ? (raw as CaseFilter) : "all";
  const open = filter !== null;
  const setCases = (value: CaseFilter | null) =>
    navigate({ pathname: location.pathname, search: withCases(location.search, value), hash: location.hash }, { replace: true });

  // Bring the case section into view once the matrix has rendered, so the
  // scroll target is the expanded section rather than the collapsed one.
  const reveal = () => {
    const section = sectionRef.current;
    if (!section) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    section.focus({ preventScroll: true });
    section.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };
  useEffect(() => {
    if (!revealPending.current || filter !== "differ") return;
    revealPending.current = false;
    reveal();
  }, [filter]);

  if (state.isLoading) return <CompareLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (state.runs.length < 2) return <ErrorState error={new Error("At least two recorded runs are needed to compare.")} />;

  const { runs, align } = state;
  const [base] = runs;
  const stats = runs.map((view) => sideStats(view.run, state.casesFor(view)));
  const diffs = runs.map((view, i) => (i === 0 ? null : caseDiff(base.run, view.run, align.shared)));
  const counts = caseCounts(lines.filter((l) => l.shared));
  const unshared = align.union.length - align.shared.length;

  const seeCases = () => {
    if (filter === "differ") return reveal();
    revealPending.current = true;
    setCases("differ");
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h2 className="text-[15px] font-medium tracking-[-0.01em]">
          {runs.length} runs against base <RunMarker index={0} className="ml-0.5 align-[-3px]" />
        </h2>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <ScopeToggle state={state} />
          <RunPicker state={state} />
        </div>
      </div>
      <CompareNotice state={state} />
      <AlignmentPanel state={state} />

      <MetricTable state={state} stats={stats} diffs={diffs} onSeeCases={seeCases} />

      <section
        ref={sectionRef}
        tabIndex={-1}
        aria-labelledby="compare-cases-title"
        className="min-w-0 scroll-mt-4 rounded-lg border border-line bg-surface outline-none"
      >
        <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <h2 id="compare-cases-title" className="text-[13.5px] font-medium">
              Case by case
            </h2>
            <p className="num mt-0.5 text-[12.5px] text-fg-3">
              {align.shared.length} shared {align.shared.length === 1 ? "case" : "cases"}
              {" · "}
              <span className={counts.differ ? "text-fg-2" : undefined}>
                {counts.differ} with different outcomes
              </span>
              {unshared > 0 && ` · ${unshared} unshared`}
            </p>
          </div>
          <button
            type="button"
            aria-expanded={open}
            aria-controls="compare-cases-body"
            onClick={() => setCases(open ? null : "all")}
            className="ml-auto inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 rounded-md border border-line px-2.5 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg"
          >
            {open ? "Show flips only" : "Show every case"}
            <ChevronDown className={clsx("size-3.5 transition-transform motion-reduce:transition-none", open && "rotate-180")} strokeWidth={1.75} />
          </button>
        </header>
        <div id="compare-cases-body">
          {open ? (
            <CaseMatrix state={state} lines={lines} filter={filter} onFilter={setCases} />
          ) : (
            <>
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-line px-4 py-2 text-[12.5px] text-fg-3">
                Ground Truth flips against the base
                <span className="inline-flex min-w-0 items-center gap-1.5">
                  <RunMarker index={0} size={15} className="!text-[9.5px]" />
                  <RunModel view={base} link={false} className="text-[12.5px]" />
                  <span>{runDate(base.run.run_id)}</span>
                </span>
                <span className="sm:ml-auto">Hover a case for what it breaks.</span>
              </p>
              <FlipLists state={state} diffs={diffs} />
            </>
          )}
        </div>
      </section>
    </div>
  );
}
