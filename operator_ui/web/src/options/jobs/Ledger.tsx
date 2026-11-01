import clsx from "clsx";
import { ArrowDown, ArrowUp, ChevronDown, ChevronUp, Search, X } from "lucide-react";
import { Dialog } from "radix-ui";
import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { displayModel } from "@/components/charts";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { StageFallback } from "../OptionsRoom";
import { inGroup, KIND_LABEL, KINDS, shortId, stamp, STATUS_GROUPS, useJobs, type Job, type StatusGroup } from "./model";
import { Chip, DemoHistoryTag, JobBody, JobProgress, KIND_ICON, KindLabel, StatusWord } from "./shared";

type SortKey = "started" | "duration";

// Columns: kind · job · status · started · duration · progress · summary (xl).
const COLS = "md:grid-cols-[minmax(0,1fr)_116px_100px_76px_120px] xl:grid-cols-[104px_minmax(200px,1.2fr)_116px_100px_76px_120px_minmax(0,1fr)]";

function liveLine(job: Job): string | undefined {
  const current = job.view?.current;
  if (job.status !== "running" || !current) return undefined;
  return `Attempt ${current.index + 1} · ${displayModel(current.model)} · ${humanize(current.caseId)}${job.view?.currentPhase ? ` · ${job.view.currentPhase.label}` : ""}`;
}

function Row({ job, selected, onOpen }: { job: Job; selected: boolean; onOpen: () => void }) {
  const live = liveLine(job);
  const summary = live ?? job.summary;
  return (
    <li>
      <button
        type="button"
        data-row
        onClick={onOpen}
        aria-haspopup="dialog"
        className={clsx(
          "grid w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-2.5 text-left transition-colors md:gap-y-0 md:py-2",
          COLS,
          selected ? "bg-accent-soft" : "hover:bg-surface-2/70",
          job.status === "running" && !selected && "bg-accent-soft/40",
        )}
      >
        <span className="hidden min-w-0 xl:block">
          <KindLabel kind={job.kind} className="max-w-full text-[12.5px]" />
        </span>
        <span className="min-w-0">
          <span className="flex min-w-0 items-center gap-2">
            {(() => {
              const Icon = KIND_ICON[job.kind];
              return <Icon className="size-3.5 shrink-0 text-fg-3 xl:hidden" strokeWidth={1.75} aria-label={KIND_LABEL[job.kind]} />;
            })()}
            <span className="truncate text-[13px] font-medium text-fg">{job.title}</span>
            <span className="ident hidden shrink-0 text-[11px] text-fg-3 xl:inline">{shortId(job.id)}</span>
          </span>
          <span className={clsx("mt-0.5 block truncate text-[12px] xl:hidden", live ? "text-fg-2" : "text-fg-3")}>{summary}</span>
        </span>
        <StatusWord job={job} className="justify-self-end md:justify-self-start" />
        <span className="num col-span-2 flex items-center gap-x-3 text-[12px] text-fg-3 md:contents">
          <span className="md:text-fg-2">{stamp(job.startMs)}</span>
          <span className="md:text-fg-2">{duration(job.durationS)}</span>
          <JobProgress job={job} className="ml-auto md:ml-0" />
        </span>
        <span className={clsx("hidden truncate text-[12px] xl:block", live ? "text-fg-2" : "text-fg-3")}>{summary}</span>
      </button>
    </li>
  );
}

function SortHeader({ label, sortKey, sort, onSort }: { label: string; sortKey: SortKey; sort: { key: SortKey; dir: "asc" | "desc" }; onSort: (key: SortKey) => void }) {
  const active = sort.key === sortKey;
  const Arrow = sort.dir === "desc" ? ArrowDown : ArrowUp;
  return (
    <button type="button" onClick={() => onSort(sortKey)} aria-label={`Sort by ${label.toLowerCase()}`} aria-pressed={active} className={clsx("inline-flex cursor-pointer items-center gap-1 rounded-[4px] text-left", active ? "text-fg-2" : "hover:text-fg-2")}>
      {label}
      {active && <Arrow className="size-3" strokeWidth={2} />}
    </button>
  );
}

function Drawer({ job, jobs, order, onClose, onSelect }: { job: Job | undefined; jobs: Job[]; order: Job[]; onClose: () => void; onSelect: (id: string) => void }) {
  const index = job ? order.findIndex((j) => j.id === job.id) : -1;
  const step = (delta: number) => {
    const next = order[index + delta];
    if (next) onSelect(next.id);
  };
  return (
    <Dialog.Root open={Boolean(job)} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <Dialog.Content
          aria-describedby={undefined}
          onKeyDown={(event) => {
            if (event.target instanceof HTMLInputElement) return;
            if (event.key === "j") {
              event.preventDefault();
              step(1);
            }
            if (event.key === "k") {
              event.preventDefault();
              step(-1);
            }
          }}
          className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-line bg-surface shadow-pop outline-none sm:w-[520px]"
        >
          {job && (
            <>
              <header className="flex items-start gap-3 border-b border-line px-5 py-4" style={{ paddingTop: "max(16px, env(safe-area-inset-top))" }}>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <KindLabel kind={job.kind} className="text-[12px]" />
                    <span className="ident text-[11px] text-fg-3">{shortId(job.id)}</span>
                  </div>
                  <Dialog.Title className="mt-1 text-[16px] leading-snug font-medium tracking-[-0.01em] text-fg">{job.title}</Dialog.Title>
                  <div className="mt-1.5">
                    <StatusWord job={job} />
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-0.5">
                  <button type="button" onClick={() => step(-1)} disabled={index <= 0} aria-label="Previous job (k)" className="grid size-8 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2 hover:text-fg disabled:cursor-default disabled:opacity-30">
                    <ChevronUp className="size-4" strokeWidth={1.75} />
                  </button>
                  <button type="button" onClick={() => step(1)} disabled={index >= order.length - 1} aria-label="Next job (j)" className="grid size-8 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2 hover:text-fg disabled:cursor-default disabled:opacity-30">
                    <ChevronDown className="size-4" strokeWidth={1.75} />
                  </button>
                  <Dialog.Close asChild>
                    <button type="button" aria-label="Close job details" className="grid size-8 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2 hover:text-fg">
                      <X className="size-4" strokeWidth={1.75} />
                    </button>
                  </Dialog.Close>
                </div>
              </header>
              <div className="flex-1 overflow-y-auto px-5 py-5" style={{ paddingBottom: "max(20px, env(safe-area-inset-bottom))" }}>
                <JobBody job={job} jobs={jobs} onSelect={onSelect} />
              </div>
              <footer className="hidden border-t border-line px-5 py-2.5 text-[11.5px] text-fg-3 sm:block">
                <kbd className="font-mono">j</kbd> / <kbd className="font-mono">k</kbd> next and previous job · <kbd className="font-mono">Esc</kbd> close
              </footer>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// A: every job in one dense, filterable table; a drawer holds the detail.
export default function Ledger() {
  const { jobs, ready } = useJobs();
  const [kind, setKind] = useState<(typeof KINDS)[number] | "all">("all");
  const [group, setGroup] = useState<StatusGroup>("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "started", dir: "desc" });
  const [openId, setOpenId] = useState<string | null>(null);
  const list = useRef<HTMLUListElement>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = jobs.filter(
      (job) =>
        (kind === "all" || job.kind === kind) &&
        inGroup(job, group) &&
        (!q || [job.title, job.id, job.summary, KIND_LABEL[job.kind], job.currentLabel ?? ""].some((text) => text.toLowerCase().includes(q))),
    );
    const value = (job: Job) => (sort.key === "started" ? job.startMs : (job.durationS ?? -1));
    return rows.sort((a, b) => (sort.dir === "desc" ? value(b) - value(a) : value(a) - value(b)));
  }, [jobs, kind, group, query, sort]);

  if (!ready) return <StageFallback />;

  const open = jobs.find((job) => job.id === openId);
  const kindCount = (k: (typeof KINDS)[number] | "all") => jobs.filter((job) => (k === "all" || job.kind === k) && inGroup(job, group)).length;
  const groupCount = (g: StatusGroup) => jobs.filter((job) => (kind === "all" || job.kind === kind) && inGroup(job, g)).length;
  const filtered = kind !== "all" || group !== "all" || query !== "";
  const onSort = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: "desc" }));

  // Arrow keys and j/k move between rows, as in a native list.
  const onListKey = (event: KeyboardEvent<HTMLUListElement>) => {
    const keys = { ArrowDown: 1, j: 1, ArrowUp: -1, k: -1 } as Record<string, number>;
    const delta = keys[event.key];
    if (!delta || !list.current) return;
    const rows = [...list.current.querySelectorAll<HTMLButtonElement>("[data-row]")];
    const at = rows.indexOf(document.activeElement as HTMLButtonElement);
    const next = rows[Math.max(0, Math.min(rows.length - 1, at + delta))];
    if (next) {
      event.preventDefault();
      next.focus();
    }
  };

  return (
    <div className="grid gap-3">
      <div className="overflow-hidden rounded-lg border border-line bg-surface">
        <div className="grid gap-2 border-b border-line px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex h-7 min-w-0 flex-1 items-center gap-2 rounded-md bg-surface-2 px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent sm:max-w-[280px]">
              <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search jobs, IDs, cases" aria-label="Search jobs" className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
              {query && (
                <button type="button" onClick={() => setQuery("")} aria-label="Clear search" className="cursor-pointer rounded-[4px] text-fg-3 hover:text-fg">
                  <X className="size-3.5" strokeWidth={1.75} />
                </button>
              )}
            </label>
            <div className="ml-auto flex items-center gap-2">
              {filtered && (
                <button
                  type="button"
                  onClick={() => {
                    setKind("all");
                    setGroup("all");
                    setQuery("");
                  }}
                  className="h-7 cursor-pointer rounded-md px-2 text-[12.5px] text-fg-3 hover:bg-surface-2 hover:text-fg"
                >
                  Clear filters
                </button>
              )}
              <DemoHistoryTag />
            </div>
          </div>
          <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 [scrollbar-width:none]" role="group" aria-label="Filter by kind">
            <Chip on={kind === "all"} onClick={() => setKind("all")} count={kindCount("all")}>
              All kinds
            </Chip>
            {KINDS.map((k) => {
              const Icon = KIND_ICON[k];
              return (
                <Chip key={k} on={kind === k} onClick={() => setKind(k)} count={kindCount(k)}>
                  <Icon className="size-3.5" strokeWidth={1.75} aria-hidden /> {KIND_LABEL[k]}
                </Chip>
              );
            })}
          </div>
          <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 [scrollbar-width:none]" role="group" aria-label="Filter by status">
            {STATUS_GROUPS.map((g) => (
              <Chip key={g.id} on={group === g.id} onClick={() => setGroup(g.id)} count={groupCount(g.id)}>
                {g.id === "attention" && <span className="size-1.5 rounded-full bg-warn" aria-hidden />}
                {g.id === "active" && <span className="size-1.5 rounded-full bg-accent" aria-hidden />}
                {g.id === "all" ? "Any status" : g.label}
              </Chip>
            ))}
          </div>
        </div>

        <div className={clsx("hidden items-center gap-x-3 border-b border-line px-4 py-2 text-[11.5px] text-fg-3 md:grid", COLS)}>
          <span className="hidden xl:block">Kind</span>
          <span>Job</span>
          <span>Status</span>
          <SortHeader label="Started" sortKey="started" sort={sort} onSort={onSort} />
          <SortHeader label="Duration" sortKey="duration" sort={sort} onSort={onSort} />
          <span>Progress</span>
          <span className="hidden xl:block">Summary</span>
        </div>
        <div className="flex items-center gap-3 border-b border-line px-4 py-1.5 text-[11.5px] text-fg-3 md:hidden">
          <span>Sort</span>
          <SortHeader label="Started" sortKey="started" sort={sort} onSort={onSort} />
          <SortHeader label="Duration" sortKey="duration" sort={sort} onSort={onSort} />
        </div>

        {visible.length ? (
          <ul ref={list} onKeyDown={onListKey} className="divide-y divide-line" aria-label="Jobs">
            {visible.map((job) => (
              <Row key={job.id} job={job} selected={job.id === openId} onOpen={() => setOpenId(job.id)} />
            ))}
          </ul>
        ) : (
          <div className="grid place-items-center gap-2 px-4 py-12 text-center">
            <p className="text-[13px] text-fg-2">No jobs match these filters.</p>
            <button
              type="button"
              onClick={() => {
                setKind("all");
                setGroup("all");
                setQuery("");
              }}
              className="h-7 cursor-pointer rounded-md border border-line-strong px-2.5 text-[12.5px] text-fg hover:bg-surface-2"
            >
              Clear filters
            </button>
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2 text-[11.5px] text-fg-3">
          <span className="num">
            {visible.length} of {jobs.length} jobs · the operator keeps the latest 30
          </span>
          <span>Times in UTC · one job runs at a time</span>
        </div>
      </div>
      <Drawer job={open} jobs={jobs} order={visible} onClose={() => setOpenId(null)} onSelect={setOpenId} />
    </div>
  );
}
