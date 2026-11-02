import clsx from "clsx";
import { ArrowUpRight, Square } from "lucide-react";
import { Popover } from "radix-ui";
import { forwardRef, useState, type ComponentPropsWithoutRef } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router";
import { Outcome, Tag, Tip } from "@/components/ui";
import { clock } from "@/demo/ReplayBar";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import { attemptLook, ModelLabel } from "../execution/shared";
import { Frames, MockDesktop, MockPhone, PreviewBar, type PreviewContext } from "./frames";
import { closeEnclosingSheet, LiveAnnouncer, LiveDot, PhaseStrip, STATE_WORD, useActiveWork, useOnExecution, type ActiveWork } from "./live";

// B: a status pill in the top bar with a popover. The shell's top bar exists
// only at 1024px and wider, so below that the same pill docks into the mobile
// header's empty right side.

type PillProps = ComponentPropsWithoutRef<"button"> & { work: ActiveWork; compact?: boolean };

export const Pill = forwardRef<HTMLButtonElement, PillProps>(function Pill({ work, compact, className, ...props }, ref) {
  const share = work.planned ? work.done / work.planned : 0;
  const idle = work.state === "idle";
  return (
    <button
      ref={ref}
      type="button"
      aria-label={idle ? "No active work" : `Active work: ${STATE_WORD[work.state]}, ${work.done} of ${work.planned} attempts, ${clock(work.elapsed)} elapsed`}
      className={clsx(
        "inline-flex h-8 cursor-pointer items-center gap-2 rounded-full border bg-surface px-3 text-[12.5px] whitespace-nowrap transition-colors hover:bg-surface-2 data-[state=open]:bg-surface-2",
        work.state === "failed" ? "border-warn/45" : idle ? "border-line" : "border-accent-line",
        className,
      )}
      {...props}
    >
      <LiveDot state={work.state} />
      {idle ? (
        <span className="text-fg-3">Idle</span>
      ) : (
        <>
          {!compact && <span className={clsx("font-medium", work.state === "failed" ? "text-warn" : "text-fg")}>{STATE_WORD[work.state]}</span>}
          {!compact && (
            <span className="h-1 w-12 overflow-hidden rounded-full bg-surface-3" aria-hidden>
              <span className={clsx("block h-full rounded-full transition-[width] duration-300", work.state === "failed" ? "bg-warn" : "bg-accent")} style={{ width: `${share * 100}%` }} />
            </span>
          )}
          <span className="num text-fg">
            {work.done}
            <span className="text-fg-3">/{work.planned}</span>
          </span>
          {!compact && <span className="num text-fg-3">{clock(work.elapsed)}</span>}
        </>
      )}
    </button>
  );
});

export function PopoverBody({ work }: { work: ActiveWork }) {
  const idle = work.state === "idle";
  const recent = work.recent.slice(0, 4);
  const stopHint = "Demo replay: Stop is disabled. On the lab, Stop asks the worker to finish the current step, run teardown, and mark the campaign stopped. Completed attempts are kept.";
  return (
    <div className="grid">
      <div className="grid gap-1 border-b border-line px-4 pt-3 pb-3">
        <div className="flex items-center gap-2">
          <span className="label !text-[10px]">Active work</span>
          <Tag tone="accent">Demo</Tag>
          <span className={clsx("ml-auto inline-flex items-center gap-1.5 text-[12px] font-medium", work.state === "failed" ? "text-warn" : idle ? "text-fg-3" : "text-fg")}>
            <LiveDot state={work.state} />
            {idle ? "Completed" : STATE_WORD[work.state]}
          </span>
        </div>
        <div className="text-[14px] font-medium tracking-[-0.01em]">{work.title}</div>
        <div className="text-[12px] text-fg-3">Campaign · serial · minh-lane</div>
      </div>

      <div className="grid gap-2 border-b border-line px-4 py-3">
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-3" role="progressbar" aria-valuenow={work.done} aria-valuemax={work.planned} aria-label="Attempts done">
          <div className={clsx("h-full rounded-full transition-[width] duration-300", work.state === "failed" ? "bg-warn" : idle ? "bg-fg-2" : "bg-accent")} style={{ width: `${(work.done / Math.max(1, work.planned)) * 100}%` }} />
        </div>
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-[12px]">
          <span className="num text-fg-2">
            {work.done} of {work.planned} attempts
          </span>
          <span className="num text-fg-3">
            {clock(work.elapsed)} elapsed{work.estimateLeft !== null ? ` · ~${duration(work.estimateLeft)} left` : ""}
          </span>
        </div>
        <div className="num text-[12px] text-fg-3">
          Ground Truth{work.state === "running" ? " so far" : ""}: <span className="text-good">{work.tally.pass} passed</span> · <span className="text-bad">{work.tally.fail} failed</span> · {work.tally.unknown} unknown
        </div>
      </div>

      {work.state === "failed" && (
        <div className="border-b border-line px-4 py-3 text-[12.5px]">
          <div className="font-medium text-warn">Runner error in attempt {(work.failedAttempt ?? 0) + 1}</div>
          <p className="mt-1 leading-relaxed text-fg-3">{work.errorText}</p>
          <p className="mt-1 text-fg-3">Teardown completed. A runner error does not count against the model.</p>
        </div>
      )}

      {work.current && (
        <div className="grid gap-2 border-b border-line px-4 py-3">
          <div className="label !text-[10px]">Current attempt</div>
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px]">
            <span className="font-medium">Attempt {work.current.index + 1}</span>
            <ModelLabel model={work.current.model} className="text-fg-2" />
          </div>
          <div className="truncate text-[12.5px] text-fg-3">{humanize(work.current.caseId)}</div>
          <PhaseStrip attempt={work.current} t={work.t} />
        </div>
      )}

      {recent.length > 0 && (
        <div className="border-b border-line px-4 py-3">
          <div className="label mb-1.5 !text-[10px]">Recent outcomes</div>
          <ul className="grid gap-1">
            {recent.map((attempt) => {
              const state = work.states[attempt.index];
              return (
                <li key={attempt.index} className="grid grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-2 text-[12px]">
                  <span className="num text-fg-3">#{attempt.index + 1}</span>
                  <span className="min-w-0 truncate text-fg-2">{humanize(attempt.caseId)}</span>
                  {state === "pass" || state === "fail" || state === "unknown" ? <Outcome outcome={state} compact /> : <span className="text-[12px] font-medium text-warn">{attemptLook(state).word}</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="grid gap-2 px-4 py-3">
        <div className="flex items-center gap-2">
          {work.state === "running" && (
            <Tip content={stopHint}>
              <span tabIndex={0} className="rounded-md">
                <button type="button" disabled aria-label="Stop campaign (disabled in the demo)" className="inline-flex h-7 cursor-not-allowed items-center gap-1.5 rounded-md border border-line-strong px-2.5 text-[12.5px] text-fg-2 opacity-60">
                  <Square className="size-3" strokeWidth={2.25} /> Stop
                </button>
              </span>
            </Tip>
          )}
          <Link
            to={idle ? "/jobs" : "/execution"}
            onClick={(e) => closeEnclosingSheet(e.currentTarget)}
            className="ml-auto inline-flex h-7 items-center gap-1.5 rounded-md bg-fg px-2.5 text-[12.5px] font-medium text-bg hover:bg-fg/85"
          >
            {idle ? "Open jobs" : "Open execution"} <ArrowUpRight className="size-3.5" strokeWidth={2} />
          </Link>
        </div>
        {work.state === "running" && <p className="text-[11.5px] leading-snug text-fg-3">Stop is disabled in the demo. On the lab it finishes the current step, then runs teardown.</p>}
      </div>
    </div>
  );
}

function PillWithPopover({ work, compact, align = "end" }: { work: ActiveWork; compact?: boolean; align?: "end" | "center" }) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <Pill work={work} compact={compact} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align={align}
          sideOffset={8}
          collisionPadding={12}
          tabIndex={-1}
          aria-label="Active work"
          // Focus the panel itself so the disabled Stop's tooltip does not open on its own.
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            (event.currentTarget as HTMLElement | null)?.focus?.();
          }}
          className="z-50 max-h-[calc(100dvh-80px)] w-[360px] max-w-[calc(100vw-24px)] overflow-y-auto rounded-lg border border-line bg-surface shadow-pop outline-none"
        >
          <PopoverBody work={work} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

/** Registered in GLOBAL for the "topbar" slot. */
export function TopbarPillGlobal() {
  const work = useActiveWork();
  const onExecution = useOnExecution();
  if (!work.ready) return null;
  // On Execution the page says everything; keep a quiet count in the sticky bar.
  const desktop = onExecution ? (
    <span className="inline-flex h-8 items-center gap-2 px-1 text-[12.5px] text-fg-2" aria-label={`${work.done} of ${work.planned} attempts`}>
      <LiveDot state={work.state} />
      <span className="num">
        {work.done}
        <span className="text-fg-3">/{work.planned}</span>
      </span>
      <span className="num text-fg-3">{clock(work.elapsed)}</span>
    </span>
  ) : (
    <PillWithPopover work={work} />
  );
  // Below 1024px the top bar is hidden; dock a compact pill into the mobile
  // header's slot (Shell renders #mobile-dock), or float it if the slot is absent.
  const slot = typeof document !== "undefined" ? document.getElementById("mobile-dock") : null;
  const mobile =
    !onExecution && typeof document !== "undefined"
      ? createPortal(
          slot ? (
            <div className="lg:hidden">
              <PillWithPopover work={work} compact />
            </div>
          ) : (
            <div className="fixed top-2 right-14 z-[35] lg:hidden">
              <PillWithPopover work={work} compact />
            </div>
          ),
          slot ?? document.body,
        )
      : null;
  return (
    <>
      {desktop}
      {mobile}
      <LiveAnnouncer work={work} />
    </>
  );
}

export default function TopbarPillOption() {
  const [context, setContext] = useState<PreviewContext>("page");
  const [open, setOpen] = useState(true);
  const work = useActiveWork(context === "idle" ? "idle" : undefined);
  const onExecution = context === "execution";
  const page = onExecution ? "Execution" : "Models";
  const pill = onExecution ? (
    <span className="inline-flex h-8 items-center gap-2 px-1 text-[12.5px] text-fg-2">
      <LiveDot state={work.state} />
      <span className="num">
        {work.done}
        <span className="text-fg-3">/{work.planned}</span>
      </span>
      <span className="num text-fg-3">{clock(work.elapsed)}</span>
    </span>
  ) : (
    <Pill work={work} aria-expanded={open} data-state={open ? "open" : "closed"} onClick={() => setOpen(!open)} />
  );
  return (
    <div className="grid gap-4">
      <PreviewBar value={context} onChange={setContext} note="The popover is shown open; click the pill to toggle it. Turn on Failure branch to see the error state." />
      <Frames
        desktop={
          <MockDesktop
            page={page}
            topbar={pill}
            overlay={
              open && !onExecution ? (
                <div className="absolute top-[52px] right-3 z-10 max-h-[480px] w-[340px] overflow-y-auto rounded-lg border border-line bg-surface shadow-pop">
                  <PopoverBody work={work} />
                </div>
              ) : null
            }
          />
        }
        phone={<MockPhone page={page} headerRight={onExecution ? null : <Pill work={work} compact />} />}
        desktopCaption="Desktop: in the top bar on every page; on Execution it shrinks to a quiet count that stays visible while the log scrolls."
        phoneCaption="Phone: a compact pill in the header; tap for the same popover. Hidden on Execution."
      />
    </div>
  );
}
