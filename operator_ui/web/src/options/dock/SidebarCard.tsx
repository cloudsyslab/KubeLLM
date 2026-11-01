import clsx from "clsx";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { displayModel } from "@/components/charts";
import { clock } from "@/demo/ReplayBar";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { Frames, MockDesktop, MockPhone, PreviewBar, type PreviewContext } from "./frames";
import { AttemptStrip, closeEnclosingSheet, LiveAnnouncer, LiveDot, PhaseStrip, useActiveWork, useOnExecution, type ActiveWork } from "./live";

// A: a compact card above the sidebar footer. It is also in the mobile
// navigation sheet, because the shell renders the same sidebar there.

export function SidebarCardView({ work, onExecution }: { work: ActiveWork; onExecution: boolean }) {
  if (!work.ready) return null;

  if (work.state === "idle") {
    return (
      <div className="px-3 pb-2">
        <Link to="/jobs" onClick={(e) => closeEnclosingSheet(e.currentTarget)} className="flex h-8 items-center gap-2 rounded-md px-2 text-[12px] text-fg-3 hover:bg-surface-2/60 hover:text-fg-2">
          <LiveDot state="idle" />
          <span className="truncate">No active work</span>
          <span className="ml-auto shrink-0">Jobs</span>
        </Link>
      </div>
    );
  }

  if (onExecution) {
    return (
      <div className="px-3 pb-2">
        <div aria-current="page" className="flex h-8 items-center gap-2 rounded-md px-2 text-[12px] text-fg-2">
          <LiveDot state={work.state} />
          <span className="truncate">{work.state === "failed" ? "Stopped on error" : "Running"}</span>
          <span className="num text-fg-3">
            {work.done}/{work.planned}
          </span>
          <span className="ml-auto shrink-0 text-fg-3">on this page</span>
        </div>
      </div>
    );
  }

  const failed = work.state === "failed";
  return (
    <div className="px-3 pb-3">
      <Link
        to="/execution"
        onClick={(e) => closeEnclosingSheet(e.currentTarget)}
        aria-label={`Active work: ${work.title}, ${failed ? "stopped on a runner error" : `${work.done} of ${work.planned} attempts done`}. Open execution.`}
        className={clsx("group block rounded-md border px-3 py-2.5 transition-colors hover:bg-surface-2/60", failed ? "border-warn/40" : "border-accent-line")}
      >
        <div className="flex items-center gap-2">
          <LiveDot state={work.state} />
          <span className={clsx("label truncate !text-[10px]", failed && "!text-warn")}>{failed ? "Stopped on error" : "Active work"}</span>
          <span className="label ml-auto !text-[9px] !text-accent">Demo</span>
        </div>
        <div className="mt-1.5 flex items-baseline justify-between gap-2">
          <span className="truncate text-[13px] text-fg">{work.title}</span>
          <span className="num shrink-0 text-[12px] text-fg-2">
            {work.done}
            <span className="text-fg-3">/{work.planned}</span>
          </span>
        </div>
        <AttemptStrip states={work.states} className="mt-1.5" />
        {failed ? (
          <p className="mt-2 text-[12px] leading-snug text-fg-3">Runner error in attempt {(work.failedAttempt ?? 0) + 1}. Teardown completed; not counted against the model.</p>
        ) : work.current ? (
          <div className="mt-2 grid gap-1 text-[12px]">
            <div className="flex min-w-0 items-baseline gap-1.5">
              <span className="shrink-0 text-fg-2">Attempt {work.current.index + 1}</span>
              <span className="ident truncate text-fg-3">{displayModel(work.current.model)}</span>
            </div>
            <div className="truncate text-fg-3">{humanize(work.current.caseId)}</div>
            <PhaseStrip attempt={work.current} t={work.t} className="mt-0.5" />
          </div>
        ) : (
          <p className="mt-2 text-[12px] text-fg-3">Between attempts</p>
        )}
        <span className="mt-2 flex items-center gap-1 text-[12px] text-fg-3">
          <span className="group-hover:text-fg">Open execution</span>
          <ArrowRight className="size-3 transition-transform group-hover:text-fg motion-safe:group-hover:translate-x-0.5" strokeWidth={2} />
          <span className="num ml-auto text-[11px]" title={work.estimateLeft !== null ? `About ${duration(work.estimateLeft)} left (estimate from the mean attempt length)` : undefined}>
            {clock(work.elapsed)}
          </span>
        </span>
      </Link>
    </div>
  );
}

/** Registered in GLOBAL for the "sidebar" slot. */
export function SidebarCardGlobal() {
  const work = useActiveWork();
  const onExecution = useOnExecution();
  return (
    <>
      <SidebarCardView work={work} onExecution={onExecution} />
      <LiveAnnouncer work={work} />
    </>
  );
}

export default function SidebarCardOption() {
  const [context, setContext] = useState<PreviewContext>("page");
  const work = useActiveWork(context === "idle" ? "idle" : undefined);
  const onExecution = context === "execution";
  const page = onExecution ? "Execution" : "Models";
  const card = <SidebarCardView work={work} onExecution={onExecution} />;
  return (
    <div className="grid gap-4">
      <PreviewBar value={context} onChange={setContext} note="Follows the replay. Turn on Failure branch to see the error state; scrub to the end for idle." />
      <Frames
        desktop={<MockDesktop page={page} sidebar={card} />}
        phone={<MockPhone page={page} sheet={card} />}
        desktopCaption="Desktop: above the sidebar footer on every page. The whole card opens Execution."
        phoneCaption="Phone: the same card inside the navigation sheet, one tap away."
      />
    </div>
  );
}
