import clsx from "clsx";
import { Check, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { displayModel } from "@/components/charts";
import { LabLogo } from "@/components/ModelCard";
import { Button, Tag } from "@/components/ui";
import { labOf } from "@/data/models";
import { count } from "@/lib/format";
import { CheckMark } from "../environment/readiness";
import {
  COMMIT_MESSAGE,
  COMMIT_PATH_COUNT,
  MODELS,
  P,
  PACK_FILE_COUNT,
  PREVIEW_TTL_MIN,
  PUBLISH_DONE,
  PUSHES_AFTER_COMMIT,
  PublishSteps,
  SHORT_ID,
  campaignLine,
  preview,
  usePreviewExpiry,
  usePublishJob,
} from "./shared";

type Stage = "preview" | "preparing" | "review" | "publishing" | "done";
const STAGES = ["Preview", "Review", "Publish", "Done"] as const;

function Line({ label, children, strong }: { label: string; children: ReactNode; strong?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 py-1 text-[13px]">
      <span className="shrink-0 text-fg-2">{label}</span>
      <span aria-hidden className="mb-1 min-w-4 flex-1 border-b border-dotted border-line-strong" />
      <span className={clsx("num min-w-0 text-right", strong ? "font-medium text-fg" : "text-fg")}>{children}</span>
    </div>
  );
}

function Perforation() {
  return (
    <div aria-hidden className="relative -mx-5 my-3 h-4">
      <span className="absolute top-1/2 -left-2 size-4 -translate-y-1/2 rounded-full border border-line bg-bg" />
      <span className="absolute top-1/2 -right-2 size-4 -translate-y-1/2 rounded-full border border-line bg-bg" />
      <span className="absolute top-1/2 right-4 left-4 border-t border-dashed border-line-strong" />
    </div>
  );
}

function Fold({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-line py-2">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex w-full cursor-pointer items-center gap-1.5 text-left text-[12.5px] text-fg-2 hover:text-fg">
        <ChevronRight className={clsx("size-3.5 transition-transform", open && "rotate-90")} strokeWidth={2} />
        {title}
      </button>
      {open && <div className="mt-2 pl-5 text-[12.5px] text-fg-2">{children}</div>}
    </div>
  );
}

function Steps({ stage }: { stage: Stage }) {
  const index = stage === "preview" || stage === "preparing" ? 0 : stage === "review" ? 1 : stage === "publishing" ? 2 : 3;
  return (
    <ol className="flex items-center gap-2 text-[12px]" aria-label="Progress">
      {STAGES.map((label, i) => (
        <li key={label} className="flex items-center gap-2" aria-current={i === index ? "step" : undefined}>
          {i > 0 && <span aria-hidden className={clsx("h-px w-5 sm:w-8", i <= index ? "bg-fg-3" : "bg-line-strong")} />}
          <span className={clsx("inline-flex items-center gap-1.5", i === index ? "text-fg" : i < index ? "text-fg-2" : "text-fg-3")}>
            <span className={clsx("grid size-4 place-items-center rounded-full text-[9.5px] font-medium", i === index ? "bg-accent text-accent-ink" : i < index ? "bg-surface-3 text-fg-2" : "border border-line-strong")}>
              {i < index ? <Check className="size-2.5" strokeWidth={3} /> : i + 1}
            </span>
            <span className={clsx(i !== index && "hidden sm:inline")}>{label}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export default function Receipt() {
  const [stage, setStage] = useState<Stage>("preview");
  const [ack, setAck] = useState(false);
  const expiry = usePreviewExpiry();
  const job = usePublishJob();
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  useEffect(() => {
    if (job.phase === "done") setStage("done");
  }, [job.phase]);

  const prepare = () => {
    setStage("preparing");
    timer.current = window.setTimeout(() => {
      preview.refresh();
      setStage("review");
    }, 1400);
  };
  const publish = () => {
    setStage("publishing");
    job.start();
  };
  const reset = () => {
    job.reset();
    setAck(false);
    setStage("preview");
  };

  return (
    <div className="grid justify-items-center gap-4 py-2">
      <div className="flex w-full max-w-[480px] flex-wrap items-center justify-between gap-3">
        <Steps stage={stage} />
        <Tag tone="accent">Demo</Tag>
      </div>

      <article className="w-full max-w-[480px] rounded-lg border border-line bg-surface px-5 py-5" aria-label="Sanitized export receipt">
        <header className="grid gap-1">
          <div className="label">Sanitized export · campaign {SHORT_ID}</div>
          <h3 className="ident text-[15px] leading-snug font-medium break-all">{P.pack}</h3>
          <p className="text-[12.5px] text-fg-3">{campaignLine}</p>
        </header>

        {(stage === "preview" || stage === "preparing") && (
          <div className="mt-5 grid gap-4">
            <p className="text-[13px] leading-relaxed text-fg-2">
              Preparing a preview copies the campaign's structured results through the sanitizer into a private folder, hashes every file, and checks that <span className="ident">{P.target.branch}</span> has no unpublished commits. Nothing in <span className="ident">data/</span> changes yet.
            </p>
            <Button variant="primary" onClick={prepare} disabled={stage === "preparing"} className="w-full">
              {stage === "preparing" ? (
                <>
                  <CheckMark running className="text-bg" /> Preparing the safe export preview…
                </>
              ) : (
                "Prepare preview"
              )}
            </Button>
            <p className="sr-only" role="status" aria-live="polite">
              {stage === "preparing" ? "Preparing the safe export preview." : ""}
            </p>
          </div>
        )}

        {stage !== "preview" && stage !== "preparing" && (
          <>
            <div className="mt-4 grid">
              <Line label="Attempts recorded">
                {P.attempts.recorded} of {P.attempts.planned}
              </Line>
              <Line label="Not started">{P.attempts.unstarted}</Line>
              <Line label="Without exportable structure">{P.attempts.excluded}</Line>
              <Line label="Ground Truth">
                {P.groundTruth.passed} passed of {P.groundTruth.known} known
              </Line>
              <Line label="Verifier agrees">
                {P.verifier.agrees} of {P.verifier.comparable}
              </Line>
              <Line label="Models">
                <span className="inline-flex flex-wrap justify-end gap-x-2.5 gap-y-1">
                  {MODELS.map((m) => (
                    <span key={m} className="inline-flex items-center gap-1">
                      <LabLogo lab={labOf(m)} size={12} />
                      <span className="ident text-[12px]">{displayModel(m)}</span>
                    </span>
                  ))}
                </span>
              </Line>
              <Line label="Pack files">{count(PACK_FILE_COUNT)}</Line>
              <Line label="Catalog edits">{P.catalogEdits.length}</Line>
              <Line label="Paths in the commit" strong>
                {count(COMMIT_PATH_COUNT)}
              </Line>
            </div>

            <Perforation />

            <dl className="grid gap-2 text-[12.5px]">
              <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-2">
                <dt className="text-fg-3">Destination</dt>
                <dd className="ident break-all text-fg">{P.destination}/</dd>
              </div>
              <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-2">
                <dt className="text-fg-3">Commit</dt>
                <dd className="text-fg-2">
                  <span className="ident text-fg">{P.target.branch}</span> at <span className="ident">{P.target.head}</span>
                  {PUSHES_AFTER_COMMIT ? ", then pushed to its upstream" : ", local only"}
                </dd>
              </div>
              <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-2">
                <dt className="text-fg-3">Preview</dt>
                <dd className={clsx("num", expiry.expired || expiry.left < 5 * 60_000 ? "text-warn" : "text-fg-2")}>{expiry.expired ? "Expired" : `Expires in ${expiry.label} (valid ${PREVIEW_TTL_MIN} min)`}</dd>
              </div>
            </dl>

            <div className="mt-3">
              <Fold title="What is inside">
                <p>
                  One folder per attempt: <span className="ident text-fg">{P.layout}</span>
                </p>
                <p className="mt-2 text-fg-3">Per attempt</p>
                <ul className="ident grid gap-0.5 text-fg">
                  {P.perAttemptFiles.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                <p className="mt-2 text-fg-3">Per case, in a folder named after the case</p>
                <ul className="ident grid gap-0.5 text-fg">
                  {P.perCaseFiles.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                <p className="mt-2 text-fg-3">Pack</p>
                <ul className="ident grid gap-0.5 text-fg">
                  {P.packFiles.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                  {P.catalogEdits.map((f) => (
                    <li key={f}>
                      {f} <span className="font-sans text-fg-3">+1 line</span>
                    </li>
                  ))}
                </ul>
              </Fold>
              <Fold title="What is left out">
                <p>{P.excluded}.</p>
                <p className="mt-2">
                  <span className="ident text-fg">run_config.archived.json</span> keeps the pack out of canonical analysis.
                </p>
              </Fold>
            </div>

            <div className="mt-3 border-t border-line pt-4">
              {stage === "review" && (
                <div className="grid gap-3">
                  <label className="flex cursor-pointer items-start gap-2.5 text-[12.5px] text-fg-2">
                    <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-[3px] size-3.5 shrink-0 cursor-pointer accent-accent" />
                    I reviewed this export. {PUSHES_AFTER_COMMIT ? "Publishing commits and pushes it." : "Publishing commits it locally."}
                  </label>
                  <Button variant="primary" className="w-full" disabled={!ack || expiry.expired} onClick={publish}>
                    Publish {count(COMMIT_PATH_COUNT)} paths
                  </Button>
                  {expiry.expired && (
                    <Button variant="ghost" className="w-full" onClick={prepare}>
                      Prepare a fresh preview
                    </Button>
                  )}
                </div>
              )}
              {(stage === "publishing" || stage === "done") && <PublishSteps phase={job.phase} step={job.step} />}
              {stage === "done" && (
                <div className="mt-4 grid justify-items-center gap-2 border-t border-dashed border-line-strong pt-4 text-center">
                  <span className="rotate-[-3deg] rounded-md border-2 border-fg px-3 py-1 font-mono text-[12px] font-semibold tracking-[0.18em] text-fg uppercase">Published</span>
                  <p className="text-[12.5px] text-fg-2">{PUBLISH_DONE}</p>
                  <p className="ident text-[11.5px] text-fg-3">“{COMMIT_MESSAGE}”</p>
                  <Button size="sm" variant="ghost" onClick={reset}>
                    Reset demo
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </article>
    </div>
  );
}
