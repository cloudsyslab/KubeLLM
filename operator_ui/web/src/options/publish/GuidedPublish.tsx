import clsx from "clsx";
import { ArrowUpRight, Check, ChevronDown, FileSearch, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { Button, Tag } from "@/components/ui";
import { count } from "@/lib/format";
import { CheckMark } from "../environment/readiness";
import { FileBrowser, README_PATH, REVIEW_CHECKS, ReviewChecklist, packNameMatches } from "./FullReview";
import { InsideAndLeftOut, ReceiptCard } from "./Receipt";
import { COMMIT_MESSAGE, COMMIT_PATH_COUNT, P, PACK_FILE_COUNT, PUBLISH_DONE, PUSHES_AFTER_COMMIT, PublishSteps, SHORT_ID, campaignLine, preview, usePreviewExpiry, usePublishJob } from "./shared";

// Publish as a guided path, like New campaign: prepare a preview, review it,
// publish, done. The receipt rides along on the right. The full review (every
// file, the exact README and catalog lines, a six-point checklist) opens
// inside the review step when wanted; while it is open, its checklist and the
// typed pack name replace the single acknowledgment.

const STEP_IDS = ["preview", "review", "publish", "done"] as const;
type StepId = (typeof STEP_IDS)[number];
type StepState = "done" | "active" | "todo";
const TITLES: Record<StepId, string> = {
  preview: "Prepare a preview",
  review: "Review the export",
  publish: "Publish",
  done: "Done",
};
const LAST = STEP_IDS.length - 1;

function Marker({ index, state }: { index: number; state: StepState }) {
  return (
    <span
      aria-hidden
      className={clsx(
        "relative z-[1] grid size-6 shrink-0 place-items-center rounded-full font-mono text-[11px] font-medium",
        state === "active" && "bg-accent text-accent-ink",
        state === "done" && "border border-line-strong bg-surface text-fg-2",
        state === "todo" && "border border-dashed border-line-strong bg-bg text-fg-3",
      )}
    >
      {state === "done" ? <Check className="size-3" strokeWidth={2.5} /> : index + 1}
    </span>
  );
}

function Step({ id, index, state, summary, onEdit, children }: { id: StepId; index: number; state: StepState; summary?: ReactNode; onEdit?: () => void; children: ReactNode }) {
  const last = index === LAST;
  return (
    <li className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-x-4" aria-current={state === "active" ? "step" : undefined}>
      {!last && <span aria-hidden className="absolute top-7 bottom-0 left-[11.5px] w-px bg-line-strong" />}
      <Marker index={index} state={state} />
      <div className={clsx("min-w-0", last ? "pb-1" : "pb-7")}>
        <div className="flex min-h-6 flex-wrap items-center justify-between gap-x-4 gap-y-1">
          <h3 id={`publish-step-${id}`} tabIndex={-1} className={clsx("scroll-mt-20 text-[14px] font-medium outline-none", state === "todo" && "text-fg-3")}>
            {TITLES[id]}
          </h3>
          {state === "done" && onEdit && (
            <button type="button" onClick={onEdit} aria-label={`Edit: ${TITLES[id].toLowerCase()}`} className="cursor-pointer text-[12.5px] text-fg-3 hover:text-fg">
              Edit
            </button>
          )}
        </div>
        {state === "done" && summary && <div className="mt-1 min-w-0 text-[12.5px] text-fg-2">{summary}</div>}
        {state === "active" && (
          <section aria-labelledby={`publish-step-${id}`} className="mt-3">
            {children}
          </section>
        )}
      </div>
    </li>
  );
}

/** The toggle that opens the full review inside the review step. */
function FullReviewToggle({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls="publish-full-review"
      onClick={onToggle}
      className={clsx("flex w-full cursor-pointer items-center gap-3 rounded-md border px-3 py-2.5 text-left transition-colors", open ? "border-accent-line bg-accent-soft" : "border-line hover:border-line-strong hover:bg-surface-2")}
    >
      <FileSearch className="size-4 shrink-0 text-fg-3" strokeWidth={1.75} />
      <span className="min-w-0 flex-1">
        <span className="block text-[13px] font-medium text-fg">{open ? "Full review" : "Open the full review"}</span>
        <span className="block text-[12px] leading-snug text-fg-3">
          Browse all {count(PACK_FILE_COUNT)} files, read the README and both catalog lines exactly, and confirm {REVIEW_CHECKS.length} points.
        </span>
      </span>
      <span className="hidden shrink-0 text-[12px] text-fg-3 sm:inline">{open ? "Hide" : "Optional"}</span>
      <ChevronDown className={clsx("size-4 shrink-0 text-fg-3 transition-transform", open && "rotate-180")} strokeWidth={1.75} />
    </button>
  );
}

function ExpiredNote({ onFresh }: { onFresh: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-md border border-warn/40 bg-warn-soft px-3 py-2 text-[12.5px] text-warn">
      <span className="min-w-0 flex-1">The preview expired. A fresh preview starts the review again, because publishing refuses anything that changed since it was reviewed.</span>
      <Button size="sm" variant="secondary" onClick={onFresh}>
        Prepare a fresh preview
      </Button>
    </div>
  );
}

export default function GuidedPublish() {
  const expiry = usePreviewExpiry();
  const job = usePublishJob();
  const [current, setCurrent] = useState(0);
  const [prep, setPrep] = useState<"none" | "preparing" | "ready">("none");
  const [ack, setAck] = useState(false);
  const [full, setFull] = useState(false);
  const [path, setPath] = useState(README_PATH);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [typed, setTyped] = useState("");
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const prepared = prep === "ready";
  const allChecked = REVIEW_CHECKS.every((c) => checked.has(c.id));
  const nameOk = packNameMatches(typed);
  const reviewed = full ? allChecked && nameOk : ack;
  const published = job.phase === "done";
  const locked = job.phase !== "idle";

  const go = (index: number) => {
    setCurrent(index);
    // Focus the opened step's heading for keyboard and screen-reader users.
    window.requestAnimationFrame(() => {
      const heading = document.getElementById("publish-step-" + STEP_IDS[index]);
      heading?.focus({ preventScroll: true });
      heading?.scrollIntoView({ block: "nearest" });
    });
  };

  useEffect(() => {
    if (job.phase === "done") go(LAST);
  }, [job.phase]);

  const clearReview = () => {
    setAck(false);
    setChecked(new Set());
    setTyped("");
  };
  const prepare = () => {
    setPrep("preparing");
    timer.current = window.setTimeout(() => {
      preview.refresh();
      setPrep("ready");
      go(1);
    }, 1400);
  };
  const fresh = () => {
    preview.refresh();
    clearReview();
    go(1);
  };
  const reset = () => {
    job.reset();
    clearReview();
    setFull(false);
    setPath(README_PATH);
    setPrep("none");
    go(0);
  };
  const toggle = (id: string, on: boolean) =>
    setChecked((s) => {
      const next = new Set(s);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const stateOf = (index: number): StepState => (published ? (index < LAST ? "done" : "active") : index === current ? "active" : index < current ? "done" : "todo");
  const expiryText = expiry.expired ? "expired" : `expires in ${expiry.label}`;
  const expiryWarn = expiry.expired || expiry.left < 5 * 60_000;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="label">Campaign {SHORT_ID}</div>
          <div className="mt-0.5 truncate text-[13.5px] text-fg">{campaignLine}</div>
        </div>
        <Tag tone="accent">Demo</Tag>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 rounded-lg border border-line bg-surface px-4 py-5 sm:px-6">
          <ol className="grid" aria-label="Publication steps">
            <Step
              id="preview"
              index={0}
              state={stateOf(0)}
              summary={
                <span>
                  Private preview prepared · <span className={clsx("num", !published && expiryWarn && "text-warn")}>{published ? "used for this publication" : expiryText}</span>
                </span>
              }
            >
              <p className="text-[13px] leading-relaxed text-fg-2">
                Preparing a preview copies the campaign's structured results through the sanitizer into a private folder, hashes every file, and checks that <span className="ident">{P.target.branch}</span> has no unpublished commits. Nothing in <span className="ident">data/</span> changes yet.
              </p>
              <div className="mt-4">
                <Button variant="primary" onClick={prepare} disabled={prep === "preparing"}>
                  {prep === "preparing" ? (
                    <>
                      <CheckMark running className="text-bg" /> Preparing the safe export preview…
                    </>
                  ) : (
                    "Prepare preview"
                  )}
                </Button>
              </div>
              <p className="sr-only" role="status" aria-live="polite">
                {prep === "preparing" ? "Preparing the safe export preview." : ""}
              </p>
            </Step>

            <Step
              id="review"
              index={1}
              state={stateOf(1)}
              onEdit={locked ? undefined : () => go(1)}
              summary={full ? `Full review: all ${REVIEW_CHECKS.length} points confirmed, pack name typed` : `Acknowledged the receipt · ${count(COMMIT_PATH_COUNT)} paths`}
            >
              <div className="grid gap-4">
                <ReceiptCard prepared={prepared} className="xl:hidden" />
                <p className="text-[13px] leading-relaxed text-fg-2">
                  The receipt counts what the commit will contain, from the sanitized copy. Check the totals, the destination, and what is left out; open the full review to read the files themselves.
                </p>
                <InsideAndLeftOut />
                <FullReviewToggle open={full} onToggle={() => setFull(!full)} />
                {full && (
                  <div id="publish-full-review" className="grid gap-4">
                    <p className="text-[12.5px] text-fg-3">While the full review is open, its checklist and the typed pack name replace the single acknowledgment. Hide it to go back.</p>
                    <FileBrowser path={path} onPath={setPath} />
                    <ReviewChecklist checked={checked} onToggle={toggle} typed={typed} onTyped={setTyped} />
                  </div>
                )}
                {!full && (
                  <label className="flex cursor-pointer items-start gap-2.5 text-[13px] text-fg-2">
                    <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-[3px] size-3.5 shrink-0 cursor-pointer accent-accent" />
                    I reviewed the receipt: the {count(COMMIT_PATH_COUNT)} paths, where they go, and what is left out.
                  </label>
                )}
                {expiry.expired && <ExpiredNote onFresh={fresh} />}
                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="primary" onClick={() => go(2)} disabled={!reviewed || expiry.expired}>
                    Continue to publish
                  </Button>
                </div>
              </div>
            </Step>

            <Step id="publish" index={2} state={stateOf(2)} summary={<span className="ident">“{COMMIT_MESSAGE}”</span>}>
              {job.phase === "idle" ? (
                <div className="grid gap-4">
                  <div className="rounded-md border border-line px-4 py-3 text-[13px] leading-relaxed text-fg-2">
                    <p>
                      Publishing commits only these <span className="num font-medium text-fg">{count(COMMIT_PATH_COUNT)} paths</span>: the {count(PACK_FILE_COUNT)} pack files under <span className="ident break-all text-fg">{P.destination}/</span> and the two catalog files,{" "}
                      {P.catalogEdits.map((f, i) => (
                        <span key={f}>
                          {i > 0 && " and "}
                          <span className="ident text-fg">{f}</span>
                        </span>
                      ))}
                      . It makes one commit on <span className="ident text-fg">{P.target.branch}</span> (HEAD <span className="ident">{P.target.head}</span>)
                      {PUSHES_AFTER_COMMIT ? (
                        <>
                          {" "}
                          and then pushes that commit to <span className="ident text-fg">{P.target.upstream}</span>.
                        </>
                      ) : (
                        "; nothing is pushed."
                      )}
                    </p>
                    {PUSHES_AFTER_COMMIT && (
                      <p className="mt-2 flex items-start gap-1.5 text-warn">
                        <TriangleAlert className="mt-[4px] size-3 shrink-0" strokeWidth={2} />
                        The push goes to the shared repository.
                      </p>
                    )}
                  </div>
                  <dl className="grid gap-1.5 text-[12.5px]">
                    <div className="grid gap-0.5 sm:grid-cols-[110px_minmax(0,1fr)] sm:gap-2">
                      <dt className="text-fg-3">Commit message</dt>
                      <dd className="ident break-words text-fg">“{COMMIT_MESSAGE}”</dd>
                    </div>
                    <div className="grid gap-0.5 sm:grid-cols-[110px_minmax(0,1fr)] sm:gap-2">
                      <dt className="text-fg-3">Checked first</dt>
                      <dd className="text-fg-2">The preview token, every file hash, both catalog files, the branch, and HEAD must still match the review, or publishing refuses.</dd>
                    </div>
                  </dl>
                  {expiry.expired && <ExpiredNote onFresh={fresh} />}
                  <div className="flex flex-wrap items-center gap-3">
                    <Button variant="primary" onClick={job.start} disabled={expiry.expired}>
                      Publish {count(COMMIT_PATH_COUNT)} paths <span className="font-mono text-[10px] tracking-[0.06em] uppercase opacity-60">Demo</span>
                    </Button>
                    <Button variant="ghost" onClick={() => go(1)}>
                      Back to review
                    </Button>
                  </div>
                </div>
              ) : (
                <PublishSteps phase={job.phase} step={job.step} />
              )}
            </Step>

            <Step id="done" index={3} state={stateOf(3)}>
              <div className="grid gap-4">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <span className="rotate-[-3deg] rounded-md border-2 border-fg px-3 py-1 font-mono text-[12px] font-semibold tracking-[0.18em] text-fg uppercase">Published</span>
                  <span className="text-[13px] text-fg-2">{PUBLISH_DONE}</span>
                </div>
                <PublishSteps phase="done" step={0} />
                <p className="text-[12.5px] text-fg-2">The explorer reads the pack as an exploratory source; canonical comparisons are unchanged.</p>
                <div className="flex flex-wrap items-center gap-3 text-[12.5px]">
                  <Link to="/" className="inline-flex items-center gap-1 text-fg-3 hover:text-fg">
                    Open Models <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
                  </Link>
                  <Button size="sm" variant="ghost" onClick={reset}>
                    Reset demo
                  </Button>
                </div>
              </div>
            </Step>
          </ol>
        </div>

        <aside className="hidden xl:sticky xl:top-[72px] xl:block xl:max-h-[calc(100dvh-88px)] xl:overflow-y-auto" aria-label="Receipt">
          <ReceiptCard prepared={prepared} published={published} />
        </aside>
      </div>
    </div>
  );
}
