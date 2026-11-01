import clsx from "clsx";
import { FileDiff, Search } from "lucide-react";
import { useId, useState } from "react";
import { Tag } from "@/components/ui";
import { count } from "@/lib/format";
import { CATALOG_DIFFS, FILE_NOTE, FileTree, MODELS, P, PACK_FILE_COUNT, PUSHES_AFTER_COMMIT, README_TEXT, illustrative, useFilteredCount } from "./shared";

// The full review: every file in the pack, the exact README and catalog
// lines, and a checklist that ends in typing the pack name.

export const README_PATH = `${P.destination}/README.md`;

function PreviewPane({ path }: { path: string }) {
  const diff = CATALOG_DIFFS.find((d) => d.path === path);
  const name = path.split("/").pop() ?? path;
  if (diff) {
    return (
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Tag>Exact</Tag>
          <span className="text-[12px] text-fg-3">{diff.how}</span>
        </div>
        <pre className="overflow-x-auto rounded-md border border-line font-mono text-[11.5px] leading-[1.7]">
          <span className="block px-3 pt-2 text-fg-3"> {diff.context}</span>
          <span className="block bg-accent-soft px-3 py-0.5 whitespace-pre-wrap text-fg">+ {diff.added}</span>
          <span className="block px-3 pb-2 text-fg-3"> …</span>
        </pre>
      </div>
    );
  }
  if (path === README_PATH) {
    return (
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Tag>Exact</Tag>
          <span className="text-[12px] text-fg-3">The template in publishing.py, filled with this preview's numbers.</span>
        </div>
        <pre className="overflow-x-auto rounded-md bg-surface-2 px-3 py-2.5 font-mono text-[11.5px] leading-[1.65] whitespace-pre-wrap text-fg-2">{README_TEXT}</pre>
      </div>
    );
  }
  const content = illustrative(path);
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Tag>Illustrative</Tag>
        <span className="text-[12px] text-fg-3">Field names are what the sanitizer keeps; values are samples.</span>
      </div>
      {FILE_NOTE[name] && <p className="text-[12.5px] text-fg-2">{FILE_NOTE[name]}.</p>}
      {content ? <pre className="overflow-x-auto rounded-md bg-surface-2 px-3 py-2.5 font-mono text-[11.5px] leading-[1.65] text-fg-2">{content}</pre> : <p className="text-[12.5px] text-fg-3">No preview for this file.</p>}
    </div>
  );
}

/** File list (catalog edits, then the pack tree) beside a preview of the selected file. */
export function FileBrowser({ path, onPath }: { path: string; onPath: (path: string) => void }) {
  const [filter, setFilter] = useState("");
  const shown = useFilteredCount(filter);
  return (
    <div className="grid items-start gap-3 md:grid-cols-[minmax(0,280px)_minmax(0,1fr)]">
      <nav aria-label="Files to publish" className="min-w-0 rounded-lg border border-line bg-surface">
        <div className="border-b border-line px-3 py-2.5">
          <div className="label !text-[10px]">Catalog edits</div>
          <ul className="mt-1.5 grid gap-0.5">
            {CATALOG_DIFFS.map((d) => (
              <li key={d.path}>
                <button type="button" aria-current={path === d.path} onClick={() => onPath(d.path)} className={clsx("flex w-full cursor-pointer items-center gap-1.5 rounded-[4px] px-1.5 py-1 text-left font-mono text-[12px]", path === d.path ? "bg-accent-soft text-fg" : "text-fg-2 hover:bg-surface-2")}>
                  <FileDiff className="size-3.5 shrink-0 text-fg-3" strokeWidth={1.75} />
                  <span className="truncate">{d.path}</span>
                  <span className="ml-auto pl-1 text-[11px] text-fg-3">+1</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <label className="flex h-9 items-center gap-2 border-b border-line px-3 text-[12.5px] text-fg-3">
          <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter by case" aria-label="Filter attempts by case" className="w-full min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
        </label>
        {filter.trim() && (
          <p className="border-b border-line px-3 py-1.5 text-[12px] text-fg-3">
            {shown} of {P.attempts.recorded} attempts match
          </p>
        )}
        <FileTree filter={filter} selected={path} onSelect={onPath} maxHeight={420} className="max-md:!max-h-[280px]" />
      </nav>

      <section className="min-w-0 rounded-lg border border-line bg-surface" aria-label="File preview">
        <header className="border-b border-line px-4 py-2.5">
          <div className="ident text-[12px] break-all text-fg">{path}</div>
        </header>
        <div className="px-4 py-3">
          <PreviewPane path={path} />
        </div>
        <p className="border-t border-line px-4 py-2 text-[11.5px] text-fg-3">The current preview API returns paths and hashes only; showing file contents needs a read endpoint for the private preview copy.</p>
      </section>
    </div>
  );
}

export const REVIEW_CHECKS: { id: string; title: string; body: string }[] = [
  { id: "paths", title: "Paths", body: `Only ${P.destination}/ (${count(PACK_FILE_COUNT)} files) and the two catalog files change.` },
  { id: "excluded", title: "Left out", body: `${P.excluded} are not in the pack.` },
  { id: "models", title: "Model identifiers", body: `${MODELS.join(", ")} may be published. The sanitizer refuses any model ID that was not reviewed.` },
  { id: "outcomes", title: "Outcomes", body: `${P.groundTruth.passed} of ${P.groundTruth.known} known attempts passed Ground Truth; the verifier agrees on ${P.verifier.agrees} of ${P.verifier.comparable}. Unknown outcomes stay unknown.` },
  { id: "marker", title: "Exploratory", body: "run_config.archived.json keeps the pack out of canonical analysis." },
  { id: "git", title: "Git", body: PUSHES_AFTER_COMMIT ? `One commit on ${P.target.branch} (HEAD ${P.target.head}), then a push to ${P.target.upstream}.` : `One local commit on ${P.target.branch} (HEAD ${P.target.head}); nothing is pushed.` },
];

export const packNameMatches = (typed: string) => typed.trim() === P.pack;

/** Six points to confirm, then the pack name typed in full. Controlled by the caller. */
export function ReviewChecklist({ checked, onToggle, typed, onTyped }: { checked: Set<string>; onToggle: (id: string, on: boolean) => void; typed: string; onTyped: (value: string) => void }) {
  const confirmId = useId();
  const nameOk = packNameMatches(typed);
  return (
    <div className="grid gap-4 rounded-lg border border-line bg-surface p-4">
      <div>
        <h4 className="text-[13.5px] font-medium">Before publishing</h4>
        <p className="mt-0.5 text-[12.5px] text-fg-3">Confirm each point, then type the pack name.</p>
      </div>
      <ul className="grid gap-x-6 gap-y-2.5 md:grid-cols-2">
        {REVIEW_CHECKS.map((c) => (
          <li key={c.id}>
            <label className="grid cursor-pointer grid-cols-[16px_minmax(0,1fr)] gap-x-2.5 text-[12.5px]">
              <input type="checkbox" checked={checked.has(c.id)} onChange={(e) => onToggle(c.id, e.target.checked)} className="mt-[3px] size-3.5 cursor-pointer accent-accent" />
              <span>
                <span className="font-medium text-fg">{c.title}</span>
                <span className="mt-0.5 block leading-snug text-fg-2">{c.body}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      <div className="grid gap-1.5 border-t border-line pt-3">
        <label htmlFor={confirmId} className="text-[12.5px] text-fg-2">
          Type <span className="ident break-all text-fg select-all">{P.pack}</span> to confirm
        </label>
        <input
          id={confirmId}
          value={typed}
          onChange={(e) => onTyped(e.target.value)}
          spellCheck={false}
          autoComplete="off"
          aria-invalid={typed.length > 0 && !nameOk}
          className={clsx("ident h-8 w-full max-w-[460px] rounded-md border bg-surface px-2.5 text-[12px] text-fg outline-none focus-visible:outline-2 focus-visible:outline-accent", typed && !nameOk ? "border-warn" : "border-line-strong")}
        />
      </div>
      <p className="text-[11.5px] text-fg-3" aria-live="polite">
        {checked.size}/{REVIEW_CHECKS.length} confirmed{nameOk ? " · name matches" : ""}
      </p>
    </div>
  );
}
