import clsx from "clsx";
import { ArrowUpRight, GitBranch, Search, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { Button, Tag, Tip } from "@/components/ui";
import type { Technique } from "@/api/types";
import { techniqueLabel } from "@/lib/explore";
import { count } from "@/lib/format";
import {
  CATALOG_DIFFS,
  COMMIT_MESSAGE,
  COMMIT_PATH_COUNT,
  FILE_NOTE,
  FileTree,
  ModelIds,
  P,
  PACK_FILE_COUNT,
  PREVIEW_TTL_MIN,
  PUSHES_AFTER_COMMIT,
  PublishSteps,
  SHORT_ID,
  campaignLine,
  preview,
  target,
  useFilteredCount,
  usePreviewExpiry,
  usePublishJob,
} from "./shared";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[112px_minmax(0,1fr)] gap-3 border-t border-line py-2 text-[12.5px] first:border-t-0">
      <dt className="text-fg-3">{label}</dt>
      <dd className="min-w-0 text-fg-2">{children}</dd>
    </div>
  );
}

export default function ReviewPanel() {
  const expiry = usePreviewExpiry();
  const job = usePublishJob();
  const [ack, setAck] = useState(false);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string | undefined>();
  const shown = useFilteredCount(filter);
  const selectedName = selected?.split("/").pop();
  const canPublish = ack && !expiry.expired && job.phase === "idle";

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="label">Campaign {SHORT_ID}</span>
            <Tag tone="accent">Demo</Tag>
          </div>
          <div className="mt-0.5 truncate text-[13.5px] text-fg">{campaignLine}</div>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[12.5px]">
          <span className={clsx("num", expiry.expired ? "text-warn" : expiry.left < 5 * 60_000 ? "text-warn" : "text-fg-2")}>
            {expiry.expired ? "Preview expired" : `Preview expires in ${expiry.label}`}
          </span>
          <Button size="sm" variant="ghost" onClick={preview.refresh} disabled={job.phase === "running"}>
            Prepare a fresh preview
          </Button>
        </div>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] xl:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <section className="rounded-lg border border-line bg-surface" aria-labelledby="pub-a-summary">
          <header className="border-b border-line px-4 py-3">
            <h3 id="pub-a-summary" className="text-[13.5px] font-medium">
              What will be published
            </h3>
            <p className="mt-0.5 text-[12.5px] text-fg-3">A sanitized exploratory pack and two catalog lines.</p>
          </header>
          <div className="grid grid-cols-3 gap-3 border-b border-line px-4 py-4">
            <div>
              <div className="label !text-[10px]">Attempts</div>
              <div className="num mt-1 text-[18px] font-medium">
                {P.attempts.recorded}
                <span className="text-[13px] font-normal text-fg-3"> / {P.attempts.planned}</span>
              </div>
              <div className="text-[11.5px] text-fg-3">recorded of planned</div>
            </div>
            <div>
              <div className="label !text-[10px]">Ground Truth</div>
              <div className="num mt-1 text-[18px] font-medium">
                {P.groundTruth.passed}
                <span className="text-[13px] font-normal text-fg-3"> / {P.groundTruth.known}</span>
              </div>
              <div className="text-[11.5px] text-fg-3">passed of known</div>
            </div>
            <div>
              <div className="label !text-[10px]">Verifier</div>
              <div className="num mt-1 text-[18px] font-medium">
                {P.verifier.agrees}
                <span className="text-[13px] font-normal text-fg-3"> / {P.verifier.comparable}</span>
              </div>
              <div className="text-[11.5px] text-fg-3">agree with GT</div>
            </div>
          </div>
          <dl className="px-4 py-2">
            <Row label="Not exported">
              {P.attempts.unstarted} planned attempts not started · {P.attempts.excluded} without exportable structure
            </Row>
            <Row label="Models">
              <ModelIds />
            </Row>
            <Row label="Technique">{P.techniques.map((t) => techniqueLabel(t as Technique)).join(", ")}</Row>
            <Row label="Destination">
              <span className="ident break-all text-fg">{P.destination}/</span>
              <span className="mt-0.5 block text-fg-3">
                Layout <span className="ident">{P.layout}</span>
              </span>
            </Row>
            <Row label="Catalog edits">
              <ul className="grid gap-0.5">
                {P.catalogEdits.map((path) => (
                  <li key={path} className="ident text-fg">
                    {path}
                  </li>
                ))}
              </ul>
            </Row>
            <Row label="Left out">{P.excluded}.</Row>
            <Row label="Marker">
              <span className="ident text-fg">run_config.archived.json</span> keeps the pack out of canonical analysis; it appears as exploratory.
            </Row>
            <Row label="Git">
              <span className="flex flex-wrap items-center gap-1.5">
                <GitBranch className="size-3.5 text-fg-3" strokeWidth={1.75} />
                <span className="ident text-fg">{P.target.branch}</span>
                <span className="text-fg-3">at</span>
                <span className="ident">{P.target.head}</span>
              </span>
              <span className="mt-0.5 block">{target}. The commit contains only the {count(COMMIT_PATH_COUNT)} listed paths.</span>
              {PUSHES_AFTER_COMMIT && (
                <span className="mt-1 flex items-start gap-1.5 text-warn">
                  <TriangleAlert className="mt-[3px] size-3 shrink-0" strokeWidth={2} />
                  Publishing pushes to the shared repository.
                </span>
              )}
            </Row>
          </dl>
        </section>

        <section className="min-w-0 rounded-lg border border-line bg-surface" aria-labelledby="pub-a-files">
          <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-line px-4 py-3">
            <div>
              <h3 id="pub-a-files" className="text-[13.5px] font-medium">
                Files
              </h3>
              <p className="mt-0.5 text-[12.5px] text-fg-3">
                {count(PACK_FILE_COUNT)} in the pack · {P.perAttemptFiles.length} per attempt, {P.perCaseFiles.length} per case · {count(COMMIT_PATH_COUNT)} paths in the commit
              </p>
            </div>
            <label className="flex h-8 min-w-0 items-center gap-2 rounded-md border border-line bg-surface px-2.5 text-[12.5px] text-fg-3 focus-within:outline-2 focus-within:outline-accent">
              <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
              <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter attempts by case" aria-label="Filter attempts by case" className="w-40 min-w-0 bg-transparent text-fg outline-none placeholder:text-fg-3" />
            </label>
          </header>
          <div className="grid xl:grid-cols-[minmax(0,1fr)_minmax(0,230px)]">
            <div className="min-w-0 border-b border-line xl:border-r xl:border-b-0">
              {filter && <p className="border-b border-line px-4 py-1.5 text-[12px] text-fg-3">{shown} of {P.attempts.recorded} attempts match</p>}
              <FileTree filter={filter} selected={selected} onSelect={setSelected} maxHeight={440} />
            </div>
            <div className="grid content-start gap-3 px-4 py-3 text-[12.5px]">
              {selectedName ? (
                <div className="grid gap-1">
                  <div className="label !text-[10px]">Selected</div>
                  <div className="ident break-all text-fg">{selectedName}</div>
                  <p className="text-fg-2">{FILE_NOTE[selectedName]}</p>
                </div>
              ) : (
                <p className="text-fg-3">Select a file to see what it holds.</p>
              )}
              <div className="grid gap-2 border-t border-line pt-3">
                <div className="label !text-[10px]">Catalog edits</div>
                {CATALOG_DIFFS.map((d) => (
                  <div key={d.path} className="grid gap-1">
                    <span className="ident text-fg">{d.path}</span>
                    <span className="text-fg-3">{d.how}</span>
                    <Tip content={d.added}>
                      <span tabIndex={0} className="line-clamp-2 rounded-[4px] bg-accent-soft/60 px-1.5 py-1 font-mono text-[11px] leading-snug text-fg-2">
                        + {d.added}
                      </span>
                    </Tip>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-line bg-surface px-4 py-3" aria-label="Publish">
        {job.phase === "idle" ? (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
            <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-2.5 text-[13px]">
              <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-[3px] size-3.5 shrink-0 cursor-pointer accent-accent" />
              <span className="text-fg-2">
                I reviewed the summary and the {count(COMMIT_PATH_COUNT)} paths. {PUSHES_AFTER_COMMIT ? `They will be committed on ${P.target.branch} and pushed.` : `They will be committed on ${P.target.branch}.`}
              </span>
            </label>
            {expiry.expired && <span className="text-[12.5px] text-warn">The preview expired; prepare a fresh one.</span>}
            <Button variant="primary" disabled={!canPublish} onClick={job.start}>
              Publish {count(COMMIT_PATH_COUNT)} paths
              <span className="font-mono text-[10px] tracking-[0.06em] uppercase opacity-60">Demo</span>
            </Button>
          </div>
        ) : (
          <div className="grid gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[13px] font-medium">{job.phase === "done" ? "Published" : "Publishing"}</span>
              <span className="ident text-[12px] text-fg-3">“{COMMIT_MESSAGE}”</span>
            </div>
            <PublishSteps phase={job.phase} step={job.step} />
            {job.phase === "done" && (
              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3 text-[12.5px]">
                <span className="text-fg-2">The explorer reads the pack as an exploratory source; canonical comparisons are unchanged.</span>
                <Link to="/" className="inline-flex items-center gap-1 text-fg-3 hover:text-fg">
                  Open Models <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
                </Link>
                <Button size="sm" variant="ghost" className="ml-auto" onClick={() => (job.reset(), setAck(false), preview.refresh())}>
                  Reset demo
                </Button>
              </div>
            )}
          </div>
        )}
      </section>
      <p className="text-[11.5px] text-fg-3">
        The preview is a private sanitized copy with a hash per file, valid for {PREVIEW_TTL_MIN} minutes. Publishing refuses if any reviewed file, either catalog file, the branch, or HEAD changed since the review.
      </p>
    </div>
  );
}
