import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import { useState, type ReactNode } from "react";
import { displayModel } from "@/components/charts";
import { LabLogo } from "@/components/ModelCard";
import { labOf } from "@/data/models";
import { count } from "@/lib/format";
import { COMMIT_PATH_COUNT, MODELS, P, PACK_FILE_COUNT, PREVIEW_TTL_MIN, PUSHES_AFTER_COMMIT, SHORT_ID, campaignLine, usePreviewExpiry } from "./shared";

// The receipt: the export's totals as line items, a perforation, then where
// the commit goes and how long the preview stays valid.

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

export function Fold({ title, children }: { title: string; children: ReactNode }) {
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

/** What the pack contains and what the sanitizer leaves out, folded away. */
export function InsideAndLeftOut() {
  return (
    <div className="border-b border-line">
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
  );
}

/**
 * The receipt card. Totals come from the private preview, so they appear only
 * once it is prepared; the destination and Git target are known before that.
 */
export function ReceiptCard({ prepared, published, className }: { prepared: boolean; published?: boolean; className?: string }) {
  const expiry = usePreviewExpiry();
  return (
    <article className={clsx("overflow-hidden rounded-lg border border-line bg-surface px-5 py-5", className)} aria-label="Sanitized export receipt">
      <header className="grid gap-1">
        <div className="label">Sanitized export · campaign {SHORT_ID}</div>
        <div className="ident text-[14.5px] leading-snug font-medium break-all text-fg">{P.pack}</div>
        <p className="text-[12.5px] text-fg-3">{campaignLine}</p>
      </header>

      {prepared ? (
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
      ) : (
        <p className="mt-4 text-[12.5px] leading-relaxed text-fg-3">The totals appear once the preview is prepared; they are counted from the sanitized copy, not from the campaign record.</p>
      )}

      <Perforation />

      <dl className="grid gap-2 text-[12.5px]">
        <div className="grid grid-cols-[84px_minmax(0,1fr)] gap-2">
          <dt className="text-fg-3">Destination</dt>
          <dd className="ident break-all text-fg">{P.destination}/</dd>
        </div>
        <div className="grid grid-cols-[84px_minmax(0,1fr)] gap-2">
          <dt className="text-fg-3">Commit</dt>
          <dd className="text-fg-2">
            <span className="ident text-fg">{P.target.branch}</span> at <span className="ident">{P.target.head}</span>
            {PUSHES_AFTER_COMMIT ? (
              <>
                , then pushed to <span className="ident text-fg">{P.target.upstream}</span>
              </>
            ) : (
              ", local only"
            )}
          </dd>
        </div>
        <div className="grid grid-cols-[84px_minmax(0,1fr)] gap-2">
          <dt className="text-fg-3">Preview</dt>
          <dd className={clsx("num", prepared && !published && (expiry.expired || expiry.left < 5 * 60_000) ? "text-warn" : "text-fg-2")}>
            {published ? "Used for this publication" : !prepared ? "Not prepared yet" : expiry.expired ? "Expired" : `Expires in ${expiry.label} (valid ${PREVIEW_TTL_MIN} min)`}
          </dd>
        </div>
      </dl>
    </article>
  );
}
