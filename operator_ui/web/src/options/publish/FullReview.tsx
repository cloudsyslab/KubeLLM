import clsx from "clsx";
import { FileDiff, Search } from "lucide-react";
import { useId, useState } from "react";
import { Button, Tag } from "@/components/ui";
import { count } from "@/lib/format";
import {
  CATALOG_DIFFS,
  COMMIT_MESSAGE,
  COMMIT_PATH_COUNT,
  FILE_NOTE,
  FileTree,
  MODELS,
  P,
  PACK_FILE_COUNT,
  PUSHES_AFTER_COMMIT,
  PublishSteps,
  README_TEXT,
  SHORT_ID,
  campaignLine,
  illustrative,
  preview,
  usePreviewExpiry,
  usePublishJob,
} from "./shared";

const README_PATH = `${P.destination}/README.md`;

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

const CHECKS: { id: string; title: string; body: string }[] = [
  { id: "paths", title: "Paths", body: `Only ${P.destination}/ (${count(PACK_FILE_COUNT)} files) and the two catalog files change.` },
  { id: "excluded", title: "Left out", body: `${P.excluded} are not in the pack.` },
  { id: "models", title: "Model identifiers", body: `${MODELS.join(", ")} may be published. The sanitizer refuses any model ID that was not reviewed.` },
  { id: "outcomes", title: "Outcomes", body: `${P.groundTruth.passed} of ${P.groundTruth.known} known attempts passed Ground Truth; the verifier agrees on ${P.verifier.agrees} of ${P.verifier.comparable}. Unknown outcomes stay unknown.` },
  { id: "marker", title: "Exploratory", body: "run_config.archived.json keeps the pack out of canonical analysis." },
  { id: "git", title: "Git", body: PUSHES_AFTER_COMMIT ? `One commit on ${P.target.branch} (HEAD ${P.target.head}), then a push to its upstream.` : `One local commit on ${P.target.branch} (HEAD ${P.target.head}); nothing is pushed.` },
];

export default function FullReview() {
  const expiry = usePreviewExpiry();
  const job = usePublishJob();
  const [path, setPath] = useState(README_PATH);
  const [filter, setFilter] = useState("");
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [typed, setTyped] = useState("");
  const confirmId = useId();
  const allChecked = CHECKS.every((c) => checked.has(c.id));
  const nameOk = typed.trim() === P.pack;
  const canPublish = allChecked && nameOk && !expiry.expired && job.phase === "idle";

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="ident truncate text-[15px] font-medium">{P.pack}</h3>
            <Tag tone="accent">Demo</Tag>
          </div>
          <p className="truncate text-[12.5px] text-fg-3">
            Campaign {SHORT_ID} · {campaignLine}
          </p>
        </div>
        <div className="flex items-center gap-3 text-[12.5px]">
          <span className={clsx("num", expiry.expired || expiry.left < 5 * 60_000 ? "text-warn" : "text-fg-2")}>{expiry.expired ? "Preview expired" : `Expires in ${expiry.label}`}</span>
          <Button size="sm" variant="ghost" onClick={preview.refresh} disabled={job.phase === "running"}>
            Refresh preview
          </Button>
        </div>
      </div>

      <div className="grid items-start gap-4 md:grid-cols-[270px_minmax(0,1fr)] xl:grid-cols-[290px_minmax(0,1fr)_300px]">
        <nav aria-label="Files to publish" className="min-w-0 rounded-lg border border-line bg-surface">
          <div className="border-b border-line px-3 py-2.5">
            <div className="label !text-[10px]">Catalog edits</div>
            <ul className="mt-1.5 grid gap-0.5">
              {CATALOG_DIFFS.map((d) => (
                <li key={d.path}>
                  <button type="button" aria-current={path === d.path} onClick={() => setPath(d.path)} className={clsx("flex w-full cursor-pointer items-center gap-1.5 rounded-[4px] px-1.5 py-1 text-left font-mono text-[12px]", path === d.path ? "bg-accent-soft text-fg" : "text-fg-2 hover:bg-surface-2")}>
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
          <FileTree filter={filter} selected={path} onSelect={setPath} maxHeight={560} />
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

        <aside className="min-w-0 rounded-lg border border-line bg-surface md:col-span-2 xl:col-span-1" aria-label="Confirm publication">
          {job.phase === "idle" ? (
            <div className="grid gap-4 p-4">
              <div>
                <h3 className="text-[13.5px] font-medium">Before publishing</h3>
                <p className="mt-0.5 text-[12.5px] text-fg-3">Confirm each point, then type the pack name.</p>
              </div>
              <ul className="grid gap-2.5">
                {CHECKS.map((c) => (
                  <li key={c.id}>
                    <label className="grid cursor-pointer grid-cols-[16px_minmax(0,1fr)] gap-x-2.5 text-[12.5px]">
                      <input
                        type="checkbox"
                        checked={checked.has(c.id)}
                        onChange={(e) =>
                          setChecked((s) => {
                            const next = new Set(s);
                            if (e.target.checked) next.add(c.id);
                            else next.delete(c.id);
                            return next;
                          })
                        }
                        className="mt-[3px] size-3.5 cursor-pointer accent-accent"
                      />
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
                  Type <span className="ident text-fg select-all">{P.pack}</span> to publish
                </label>
                <input
                  id={confirmId}
                  value={typed}
                  onChange={(e) => setTyped(e.target.value)}
                  spellCheck={false}
                  autoComplete="off"
                  aria-invalid={typed.length > 0 && !nameOk}
                  className={clsx("ident h-8 rounded-md border bg-surface px-2.5 text-[12px] text-fg outline-none focus-visible:outline-2 focus-visible:outline-accent", typed && !nameOk ? "border-warn" : "border-line-strong")}
                />
              </div>
              {expiry.expired && <p className="text-[12.5px] text-warn">The preview expired. Refresh it and review again.</p>}
              <Button variant="primary" disabled={!canPublish} onClick={job.start}>
                Publish {count(COMMIT_PATH_COUNT)} paths <span className="font-mono text-[10px] tracking-[0.06em] uppercase opacity-60">Demo</span>
              </Button>
              <p className="text-[11.5px] text-fg-3">
                {checked.size}/{CHECKS.length} confirmed{nameOk ? " · name matches" : ""}
              </p>
            </div>
          ) : (
            <div className="grid gap-3 p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-[13.5px] font-medium">{job.phase === "done" ? "Published" : "Publishing"}</h3>
                <Tag tone="accent">Demo</Tag>
              </div>
              <p className="ident text-[11.5px] text-fg-3">“{COMMIT_MESSAGE}”</p>
              <PublishSteps phase={job.phase} step={job.step} />
              {job.phase === "done" && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="justify-self-start"
                  onClick={() => {
                    job.reset();
                    setChecked(new Set());
                    setTyped("");
                    preview.refresh();
                  }}
                >
                  Reset demo
                </Button>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
