import clsx from "clsx";
import { ArrowUpRight, ChevronDown, ChevronUp, X } from "lucide-react";
import { useCallback, useState, type CSSProperties } from "react";
import { Link } from "react-router";
import { Tag } from "@/components/ui";
import { clock } from "@/demo/ReplayBar";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { ModelLabel } from "../execution/shared";
import { Frames, MockDesktop, MockPhone, PreviewBar, type PreviewContext } from "./frames";
import { AttemptStrip, LiveAnnouncer, LiveDot, PhaseStrip, STATE_WORD, useActiveWork, useMediaQuery, useOnExecution, type ActiveWork } from "./live";

// C: a bottom-right mini panel that collapses to a pill. Below 640px it is
// always the pill, which opens Execution instead of expanding over content.

const STORAGE_KEY = "kubellm-dock-floating-collapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeCollapsed(value: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
  } catch {
    /* storage unavailable: the choice lasts for this page only */
  }
}

const PILL = "inline-flex h-9 cursor-pointer items-center gap-2 rounded-full border bg-surface px-3 text-[12.5px] whitespace-nowrap shadow-pop transition-colors hover:bg-surface-2";

function pillBorder(work: ActiveWork) {
  return work.state === "failed" ? "border-warn/45" : work.state === "idle" ? "border-line" : "border-accent-line";
}

export function FloatingPill({ work, mode, onExpand, onDismiss }: { work: ActiveWork; mode: "expand" | "link"; onExpand?: () => void; onDismiss?: () => void }) {
  const idle = work.state === "idle";
  const label = idle ? `Campaign completed, ${work.done} of ${work.planned} attempts` : `Active work: ${STATE_WORD[work.state]}, ${work.done} of ${work.planned} attempts`;
  const inner = (
    <>
      <LiveDot state={work.state} />
      {idle ? <span className="text-fg-2">Completed</span> : work.state === "failed" && <span className="font-medium text-warn">Stopped on error</span>}
      <span className="num text-fg">
        {work.done}
        <span className="text-fg-3">/{work.planned}</span>
      </span>
      {!idle && <span className="num text-fg-3">{clock(work.elapsed)}</span>}
    </>
  );
  return (
    <span className="inline-flex items-center gap-1">
      {mode === "link" || idle ? (
        <Link to={idle ? "/jobs" : "/execution"} aria-label={`${label}. ${idle ? "Open jobs" : "Open execution"}.`} className={clsx(PILL, pillBorder(work))}>
          {inner}
          <ArrowUpRight className="size-3.5 text-fg-3" strokeWidth={1.75} />
        </Link>
      ) : (
        <button type="button" onClick={onExpand} aria-expanded={false} aria-label={`${label}. Expand.`} className={clsx(PILL, pillBorder(work))}>
          {inner}
          <ChevronUp className="size-3.5 text-fg-3" strokeWidth={1.75} />
        </button>
      )}
      {onDismiss && (idle || work.state === "failed") && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss" className="grid size-7 cursor-pointer place-items-center rounded-full border border-line bg-surface text-fg-3 shadow-pop hover:text-fg">
          <X className="size-3.5" strokeWidth={1.75} />
        </button>
      )}
    </span>
  );
}

export function FloatingPanelView({ work, onCollapse }: { work: ActiveWork; onCollapse: () => void }) {
  const failed = work.state === "failed";
  return (
    <section aria-label="Active work" className={clsx("w-[320px] overflow-hidden rounded-lg border bg-surface shadow-pop", failed ? "border-warn/45" : "border-line")}>
      <header className="flex items-center gap-2 border-b border-line py-1.5 pr-1.5 pl-3">
        <LiveDot state={work.state} />
        <span className={clsx("label !text-[10px]", failed && "!text-warn")}>{failed ? "Stopped on error" : "Active work"}</span>
        <Tag tone="accent">Demo</Tag>
        <button type="button" onClick={onCollapse} aria-expanded aria-label="Collapse to a pill" className="ml-auto grid size-7 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2 hover:text-fg">
          <ChevronDown className="size-4" strokeWidth={1.75} />
        </button>
      </header>
      <div className="grid gap-2.5 px-3 py-3">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-[13px] font-medium">{work.title}</span>
          <span className="num shrink-0 text-[12px] text-fg-2">
            {work.done}
            <span className="text-fg-3">/{work.planned}</span>
          </span>
        </div>
        <div className="grid gap-1">
          <AttemptStrip states={work.states} outcomes cell="h-2" />
          <span className="num text-[11.5px] text-fg-3">
            <span className="text-good">{work.tally.pass} passed</span> · <span className="text-bad">{work.tally.fail} failed</span> · {work.tally.unknown} unknown
          </span>
        </div>
        {failed ? (
          <div className="grid gap-1 text-[12px] leading-snug">
            <p className="font-medium text-warn">Runner error in attempt {(work.failedAttempt ?? 0) + 1}</p>
            <p className="font-mono text-[11px] break-words text-fg-3">{work.errorText}</p>
            <p className="text-fg-3">Teardown completed; not counted against the model.</p>
          </div>
        ) : work.current ? (
          <div className="grid gap-1.5 rounded-md bg-surface-2 px-2.5 py-2">
            <div className="flex min-w-0 items-center gap-2 text-[12px]">
              <span className="shrink-0 font-medium">Attempt {work.current.index + 1}</span>
              <ModelLabel model={work.current.model} className="text-fg-2" />
            </div>
            <div className="truncate text-[12px] text-fg-3">{humanize(work.current.caseId)}</div>
            <PhaseStrip attempt={work.current} t={work.t} />
          </div>
        ) : null}
        {work.lastLine && !failed && (
          <p className="truncate font-mono text-[11px] text-fg-3" title={work.lastLine.text}>
            {work.lastLine.level === "command" && <span className="select-none">$ </span>}
            {work.lastLine.text}
          </p>
        )}
      </div>
      <footer className="flex items-center gap-2 border-t border-line px-3 py-2 text-[12px]">
        <span className="num text-fg-3">
          {clock(work.elapsed)}
          {work.estimateLeft !== null && ` · ~${duration(work.estimateLeft)} left`}
        </span>
        <Link to="/execution" className="ml-auto inline-flex items-center gap-1 rounded-[4px] text-fg-2 hover:text-fg">
          Open execution <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
        </Link>
      </footer>
    </section>
  );
}

const POSITION: CSSProperties = {
  right: "max(16px, calc(env(safe-area-inset-right) + 12px))",
  bottom: "max(16px, calc(env(safe-area-inset-bottom) + 12px))",
};

/** Registered in GLOBAL for the "floating" slot. */
export function FloatingPanelGlobal() {
  const work = useActiveWork();
  const onExecution = useOnExecution();
  const wide = useMediaQuery("(min-width: 640px)");
  const [collapsed, setCollapsedState] = useState(readCollapsed);
  const [dismissed, setDismissed] = useState<string | null>(null);
  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value);
    writeCollapsed(value);
  }, []);

  const key = `${work.state}`;
  if (!work.ready || onExecution || (work.state !== "running" && dismissed === key)) return <LiveAnnouncer work={work} />;
  const asPill = !wide || collapsed || work.state === "idle";
  return (
    <>
      <div className="fixed z-[25] flex justify-end" style={POSITION}>
        {asPill ? (
          <FloatingPill work={work} mode={wide ? "expand" : "link"} onExpand={() => setCollapsed(false)} onDismiss={() => setDismissed(key)} />
        ) : (
          <FloatingPanelView work={work} onCollapse={() => setCollapsed(true)} />
        )}
      </div>
      <LiveAnnouncer work={work} />
    </>
  );
}

export default function FloatingPanelOption() {
  const [context, setContext] = useState<PreviewContext>("page");
  const [collapsed, setCollapsed] = useState(false);
  const work = useActiveWork(context === "idle" ? "idle" : undefined);
  const onExecution = context === "execution";
  const page = onExecution ? "Execution" : "Models";
  const desktopFloating = onExecution ? null : (
    <div className="absolute right-3 bottom-3 z-10">
      {collapsed || work.state === "idle" ? <FloatingPill work={work} mode="expand" onExpand={() => setCollapsed(false)} /> : <FloatingPanelView work={work} onCollapse={() => setCollapsed(true)} />}
    </div>
  );
  const phoneFloating = onExecution ? null : (
    <div className="absolute right-3 bottom-3 z-10">
      <FloatingPill work={work} mode="link" />
    </div>
  );
  return (
    <div className="grid gap-4">
      <PreviewBar value={context} onChange={setContext} note="Collapse and expand it here; on the real pages the choice is remembered. Turn on Failure branch to see the error state." />
      <Frames
        desktop={<MockDesktop page={page} floating={desktopFloating} />}
        phone={<MockPhone page={page} floating={phoneFloating} />}
        desktopCaption="Desktop: bottom-right on every page except Execution; collapses to a pill and remembers it. Completed and error pills can be dismissed."
        phoneCaption="Phone: always the small pill, inside the safe area; tapping it opens Execution."
      />
    </div>
  );
}
