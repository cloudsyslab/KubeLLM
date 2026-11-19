import clsx from "clsx";
import { useEffect, useRef } from "react";
import { api } from "@/api/client";
import { Tag, Tip } from "@/components/ui";
import type { DemoEvent } from "@/demo/campaign";
import { executionOf, type CheckExecution } from "@/demo/readiness";
import { LogLine } from "../execution/shared";
import { depOfCheck } from "./board";
import { CheckMark, LANE, LEVEL_WORD, REPAIRS, ms, repairsFor, type CheckLevel, type ReadinessCheck, type RepairResult } from "./readiness";

// A check's terminal: the processes it ran with their stdin (the command
// line), stdout, stderr, and exit code, drawn with Execution's output lines so
// every stream in the app reads the same way. Readiness never uses the Ground
// Truth colors: stderr and nonzero exits are amber, everything else neutral.

type Line = Pick<DemoEvent, "source" | "level" | "text">;

const PY = ".venv/bin/python";

function observedExecution(commands?: ReadinessCheck["commands"]): CheckExecution {
  if (!commands?.length) return { note: "The readiness check did not return command output.", commands: [] };
  const output: CheckExecution["commands"] = [];
  for (const item of commands) {
    if (item.parent_command) output.push({ cmd: item.parent_command });
    if (item.command || item.stdout || item.stderr || item.exit_code != null) {
      output.push({
        cmd: item.command ?? item.note ?? "In-process check",
        stdout: item.stdout ? item.stdout.split("\n") : undefined,
        stderr: item.stderr ? item.stderr.split("\n") : undefined,
        exit: item.exit_code ?? undefined,
      });
    }
  }
  const notes = commands.map((item) => item.note).filter((value): value is string => Boolean(value));
  return { note: notes.join(" · ") || undefined, commands: output };
}

/** Representative commands for preparation's repairs, after check_readiness.py --repair-safe. */
function repairExecution(repair: RepairResult): CheckExecution {
  const status = { cmd: `minikube -p ${LANE.profile} status --format={{.Host}}` };
  const dataRoot = { cmd: "docker info --format {{.DockerRootDir}}", stdout: ["/var/lib/docker"], exit: 0 };
  switch (repair.name) {
    case "minikube_profile":
      if (!repair.ok) return { note: "Free space is read in process with shutil.disk_usage.", commands: [{ ...status, stdout: ["Stopped"], exit: 7 }, dataRoot], result: { stderr: ["free: 11.2 GiB; minikube start was not run."] } };
      if (repair.message.startsWith("Started"))
        return {
          commands: [
            { ...status, stdout: ["Stopped"], exit: 7 },
            dataRoot,
            { cmd: `minikube -p ${LANE.profile} start --driver=docker --keep-context`, stdout: [`* Using the docker driver based on existing profile`, `* Restarting existing docker container for "${LANE.profile}" ...`, "* Verifying Kubernetes components..."], exit: 0 },
            { ...status, stdout: ["Running"], exit: 0 },
          ],
        };
      return { note: "Long JSON output is elided.", commands: [{ ...status, stdout: ["Running"], exit: 0 }, { cmd: `docker inspect ${LANE.profile} --format '{{json .}}'`, stdout: [`{"Name": "/${LANE.profile}", "State": {"Running": true, …}, …}`], exit: 0 }] };
    case "kubeconfig":
      return {
        note: "The kubeconfig is written in process with mode 0600; long JSON output is elided.",
        commands: [
          { cmd: `docker inspect ${LANE.profile} --format '{{json .}}'`, stdout: [`{"Name": "/${LANE.profile}", "State": {"Running": true, …}, …}`], exit: 0 },
          { cmd: `kubectl --kubeconfig ${LANE.kubeconfig} get nodes --request-timeout=10s -o name`, stdout: [`node/${LANE.profile}`], exit: 0 },
        ],
      };
    case "rag_api":
      return {
        note: "HTTP probes are shown as curl equivalents. The server keeps running in the background; its output goes to its log under .local/services/.",
        commands: [
          { cmd: `curl -s ${LANE.ragApi}/server_info/`, stderr: ["curl: (7) Failed to connect to 127.0.0.1 port 18004 after 0 ms: Couldn't connect to server"], exit: 7 },
          { cmd: `RAG_SERVER_HOST=127.0.0.1 RAG_SERVER_PORT=18004 ${PY} start_apiserver.py --lab-config ${LANE.selector}`, stdout: [`started in the background · log .local/services/rag-${LANE.id}.log`] },
          { cmd: `curl -s ${LANE.ragApi}/server_info/`, stdout: ['{"api_version": "…", "server_port": 18004, "server_bind_host": "127.0.0.1", …}'], exit: 0 },
        ],
      };
    default:
      return { note: "Decided in process; no command runs.", commands: [] };
  }
}

function linesOf(exec: CheckExecution, verdict: Line): Line[] {
  const out: Line[] = [];
  for (const command of exec.commands) {
    const source: DemoEvent["source"] = command.cmd.startsWith("kubectl") ? "kubectl" : "runner";
    out.push({ source, level: "command", text: command.cmd });
    command.stdout?.forEach((text) => out.push({ source, level: "output", text }));
    command.stderr?.forEach((text) => out.push({ source, level: command.exit ? "error" : "warn", text }));
    if (command.exit !== undefined) out.push({ source, level: command.exit ? "error" : "output", text: `exit ${command.exit}` });
  }
  exec.result?.stdout?.forEach((text) => out.push({ source: "runner", level: "output", text }));
  exec.result?.stderr?.forEach((text) => out.push({ source: "runner", level: "warn", text }));
  out.push(verdict);
  return out;
}

const VERDICT_LEVEL: Record<CheckLevel, DemoEvent["level"]> = { pass: "info", warn: "warn", block: "error", skip: "info" };

export type TerminalSubject = { kind: "check"; check: ReadinessCheck } | { kind: "repair"; repair: RepairResult };

/**
 * The terminal for one check or repair. `offset` is where it starts in the
 * run, in milliseconds, so the clock column reads as elapsed run time.
 * `progress` (0 to 1) reveals the lines of a check that is still running;
 * `pending` means it has not started.
 */
export function Terminal({ subject, offset, progress, pending, className }: { subject: TerminalSubject; offset: number; progress?: number; pending?: boolean; className?: string }) {
  const isCheck = subject.kind === "check";
  const exec = isCheck
    ? api.isLive ? observedExecution(subject.check.commands) : executionOf(subject.check)
    : api.isLive ? observedExecution(subject.repair.commands) : repairExecution(subject.repair);
  const duration = isCheck ? subject.check.ms : subject.repair.ms;
  const level: CheckLevel = isCheck ? subject.check.level : subject.repair.ok ? "pass" : "block";
  const verdict: Line = isCheck
    ? { source: "runner", level: VERDICT_LEVEL[level], text: `→ ${LEVEL_WORD[level]}: ${subject.check.detail}` }
    : { source: "runner", level: subject.repair.ok ? "info" : "warn", text: `→ ${subject.repair.ok ? "Repaired" : "Not repaired"}: ${subject.repair.message}` };
  const all = linesOf(exec, verdict);
  const running = progress !== undefined;
  // While running, the verdict waits for the end and the lines arrive over the check's duration.
  const shown = pending ? [] : running ? all.slice(0, Math.max(1, Math.min(all.length - 1, Math.ceil(progress * (all.length - 1))))) : all;
  const events: DemoEvent[] = shown.map((line, i) => ({ ...line, t: (offset + (duration * i) / Math.max(1, all.length - 1)) / 1000, attempt: 0, phase: "setup" }));

  const dep = isCheck ? depOfCheck(subject.check.id) : undefined;
  const repairs = isCheck ? repairsFor(subject.check.id) : REPAIRS.filter((r) => r.name === subject.repair.name);
  const title = isCheck ? subject.check.label : subject.repair.label;
  const mono = isCheck && (subject.check.group === "live" || subject.check.group === "static");

  // What preparation can do about a finished check that did not pass.
  const advice =
    isCheck && !pending && !running && level !== "pass" ? (
      repairs.length > 0 ? (
        <div className="grid gap-1">
          <span className="label !text-[10px]">Preparation may</span>
          {repairs.map((r) => (
            <span key={r.name} className="text-fg-2">
              {r.does} <span className="text-fg-3">{r.limit}</span>
            </span>
          ))}
        </div>
      ) : (
        <p className="text-fg-2">Preparation does not change this. Fix it on the lab, then run preflight again.</p>
      )
    ) : null;

  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scroller.current;
    if (el && running) el.scrollTop = el.scrollHeight;
  }, [running, shown.length]);

  return (
    <section aria-label={`Terminal output: ${title}`} className={clsx("min-w-0 overflow-hidden rounded-md border border-line bg-bg/40", className)}>
      <header className="grid gap-1 border-b border-line px-3 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <CheckMark level={pending || running ? undefined : level} running={running} pending={pending} />
          <h4 className={clsx("min-w-0 truncate text-[13px] font-medium text-fg", mono && "ident")}>{title}</h4>
          {!isCheck && <span className="ident shrink-0 text-[11px] text-fg-3">{subject.repair.name}</span>}
          <span className={clsx("shrink-0 text-[12px]", pending ? "text-fg-3" : running ? "text-accent" : level === "pass" ? "text-fg-2" : "text-warn")}>
            {pending ? "Waiting" : running ? "Running" : isCheck ? LEVEL_WORD[level] : subject.repair.ok ? "Repaired" : "Not repaired"}
          </span>
          {!pending && !running && <span className="num shrink-0 text-[11.5px] text-fg-3">{ms(duration)}</span>}
          {!api.isLive && <span className="ml-auto shrink-0"><Tag tone="accent">Demo</Tag></span>}
        </div>
        {dep && (
          <p className="truncate text-[12px] text-fg-3">
            {dep.name} · <span className="ident">{dep.identity}</span>
          </p>
        )}
        {!api.isLive && exec.via && (
          <Tip content={exec.via}>
            <p tabIndex={0} className="truncate text-[11.5px] text-fg-3">
              Inside <span className="ident text-fg-2">runner.py --preflight</span>, run with the lane's <span className="ident">--lab-config</span>
            </p>
          </Tip>
        )}
      </header>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-3 py-1.5 text-[11.5px] text-fg-3" aria-hidden>
        <span><span className="font-mono">$</span> command</span>
        <span>stdout</span>
        <span className="text-warn">stderr</span>
        <span>times are elapsed in the run</span>
        <span className="ml-auto">Credentials redacted</span>
      </div>
      <div ref={scroller} role="log" aria-label={`${title} output`} className="max-h-[360px] overflow-y-auto px-3 py-2">
        {events.length ? (
          events.map((event, i) => <LogLine key={i} event={event} dense live={running && i === events.length - 1} />)
        ) : (
          <p className="py-6 text-center text-[12.5px] text-fg-3">{pending ? "Not run yet in this pass." : "No output."}</p>
        )}
      </div>
      {(exec.note || advice) && (
        <footer className="grid gap-2 border-t border-line px-3 py-2.5 text-[12px]">
          {advice}
          {exec.note && <p className="text-fg-3">{exec.note}</p>}
        </footer>
      )}
    </section>
  );
}
