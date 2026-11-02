import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight, Search } from "lucide-react";
import { Dialog } from "radix-ui";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { api } from "@/api/client";
import cases from "@/data/cases.json";
import { labOf } from "@/data/models";
import { JOBS, KIND_LABEL } from "@/demo/jobs";
import { humanize } from "@/lib/cases";
import { buildConfigs, techniqueLabel } from "@/lib/explore";
import { pct, runDate } from "@/lib/format";
import { SURFACES } from "@/options/registry";
import { displayModel } from "./charts";
import { LabLogo } from "./ModelCard";

interface Item {
  id: string;
  group: "Pages" | "Models" | "Runs" | "Cases" | "Jobs";
  title: string;
  detail?: string;
  icon?: ReactNode;
  to: string;
  haystack: string;
}

const CASE_TITLES = (cases as unknown as { cases: Record<string, { title: string }> }).cases;

function score(item: Item, query: string): number {
  if (!query) return 1;
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  let total = 0;
  for (const word of words) {
    const at = item.haystack.indexOf(word);
    if (at < 0) return 0;
    total += at === 0 ? 3 : item.haystack.includes(` ${word}`) ? 2 : 1;
  }
  return total;
}

// ⌘K: jump to any page, model, run, case, or job.
export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const navigate = useNavigate();
  const runs = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const list = useRef<HTMLDivElement>(null);

  const items = useMemo<Item[]>(() => {
    const pages: Item[] = [
      { id: "page-models", group: "Pages", title: "Models", detail: "Evaluate", to: "/", haystack: "models explorer leaderboard evaluate" },
      ...SURFACES.filter((s) => s.path).map((s) => ({ id: `page-${s.id}`, group: "Pages" as const, title: s.title, detail: s.group, to: s.path!, haystack: `${s.title} ${s.label} ${s.group}`.toLowerCase() })),
      { id: "page-options", group: "Pages", title: "Options room", detail: "Design review", to: "/options", haystack: "options room design review picks" },
    ];
    const configs = runs.data ? buildConfigs(runs.data, "all") : [];
    const models: Item[] = configs.map((c) => ({
      id: `model-${c.key}`,
      group: "Models",
      title: displayModel(c.debug),
      detail: `${techniqueLabel(c.technique)} · ${c.source} · ${pct(c.rate, 0)} Ground Truth`,
      icon: <LabLogo lab={labOf(c.debug)} size={14} />,
      to: `/models/${c.slug}`,
      haystack: `${c.debug} ${c.technique} ${c.source} ${labOf(c.debug)?.name ?? ""}`.toLowerCase(),
    }));
    const runItems: Item[] = (runs.data ?? []).map((r) => ({
      id: `run-${r.ref}`,
      group: "Runs",
      title: `${runDate(r.run_id)} · ${displayModel(r.models.DebugAgent[0] ?? "unrecorded")}`,
      detail: `${r.source} · ${pct(r.ground_truth_rate, 0)} of ${r.ground_truth_known} known`,
      to: `/runs/${r.ref}`,
      haystack: `${r.run_id} ${r.models.DebugAgent.join(" ")} ${r.source} ${r.technique ?? ""}`.toLowerCase(),
    }));
    const caseItems: Item[] = Object.entries(CASE_TITLES).map(([id, info]) => ({
      id: `case-${id}`,
      group: "Cases",
      title: humanize(id),
      detail: info.title || "Benchmark case",
      to: `/?case=${id}`,
      haystack: `${id} ${humanize(id)} ${info.title}`.toLowerCase(),
    }));
    const jobs: Item[] = JOBS.map((job) => ({
      id: `job-${job.id}`,
      group: "Jobs",
      title: job.title,
      detail: `${KIND_LABEL[job.kind]} · ${job.status}`,
      to: job.live ? "/execution" : `/jobs?job=${job.id}`,
      haystack: `${job.title} ${job.kind} ${job.status} ${job.id}`.toLowerCase(),
    }));
    return [...pages, ...models, ...runItems, ...caseItems, ...jobs];
  }, [runs.data]);

  const results = useMemo(() => {
    const scored = items.map((item) => ({ item, s: score(item, query.trim()) })).filter((r) => r.s > 0);
    const limits: Record<Item["group"], number> = { Pages: query ? 6 : 12, Models: 6, Runs: query ? 8 : 0, Cases: query ? 6 : 0, Jobs: query ? 5 : 0 };
    const out: Item[] = [];
    for (const group of ["Pages", "Models", "Runs", "Cases", "Jobs"] as const) {
      out.push(...scored.filter((r) => r.item.group === group).sort((a, b) => b.s - a.s).slice(0, limits[group]).map((r) => r.item));
    }
    return out;
  }, [items, query]);

  useEffect(() => setActive(0), [query, open]);
  useEffect(() => {
    list.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const go = (item: Item | undefined) => {
    if (!item) return;
    onOpenChange(false);
    setQuery("");
    navigate(item.to);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed top-[12vh] left-1/2 z-50 w-[min(640px,calc(100vw-24px))] -translate-x-1/2 overflow-hidden rounded-lg bg-surface-2 shadow-pop"
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setActive((i) => Math.min(results.length - 1, i + 1));
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setActive((i) => Math.max(0, i - 1));
            } else if (event.key === "Enter") {
              event.preventDefault();
              go(results[active]);
            }
          }}
        >
          <Dialog.Title className="sr-only">Search KubeLLM</Dialog.Title>
          <div className="flex items-center gap-2.5 border-b border-line px-4">
            <Search className="size-4 text-fg-3" strokeWidth={1.75} />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search pages, models, runs, cases, jobs"
              aria-label="Search"
              className="h-12 w-full bg-transparent text-[14px] text-fg outline-none placeholder:text-fg-3"
            />
            <kbd className="rounded border border-line-strong px-1.5 font-mono text-[10.5px] text-fg-3">esc</kbd>
          </div>
          <div ref={list} className="max-h-[60vh] overflow-y-auto py-1.5" role="listbox" aria-label="Results">
            {results.map((item, index) => {
              const first = index === 0 || results[index - 1].group !== item.group;
              return (
                <div key={item.id}>
                  {first && <div className="label px-4 pt-2.5 pb-1 !text-[10px]">{item.group}</div>}
                  <button
                    type="button"
                    data-index={index}
                    role="option"
                    aria-selected={index === active}
                    onMouseMove={() => setActive(index)}
                    onClick={() => go(item)}
                    className={clsx("mx-1.5 flex w-[calc(100%-12px)] cursor-pointer items-center gap-3 rounded-md px-2.5 py-2 text-left", index === active ? "bg-surface-3" : "")}
                  >
                    {item.icon ?? <span className="size-3.5" />}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] text-fg">{item.title}</span>
                      {item.detail && <span className="block truncate text-[12px] text-fg-3">{item.detail}</span>}
                    </span>
                    {index === active && <ArrowRight className="size-3.5 text-fg-3" strokeWidth={1.75} />}
                  </button>
                </div>
              );
            })}
            {!results.length && <p className="px-4 py-8 text-center text-[13px] text-fg-3">Nothing matches “{query}”.</p>}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function useCommandPaletteHotkey(setOpen: (fn: (open: boolean) => boolean) => void) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);
}
