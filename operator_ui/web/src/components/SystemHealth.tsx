import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { Popover } from "radix-ui";
import { useState, type ReactNode } from "react";
import { Link } from "react-router";
import { api, snapshotGeneratedAt } from "@/api/client";
import type { TelemetrySample, TopologySnapshot } from "@/api/types";
import { HOST } from "@/demo/lab";
import { HEALTH, type Health, type TopologyGraph } from "@/demo/topologyGraph";
import { useGraph } from "@/options/topology/shared";
import { CheckMark, LEVEL_WORD, freshnessLine, groupChecks, stamp, useFreshness, type Freshness } from "@/options/environment/readiness";
import { Tag } from "./ui";

// "Is everything healthy?" in the sidebar corner. Built from the same sources
// the pages read, so it never disagrees with them: lane health is Topology's
// lane rollup, preflight is the shared readiness store that Environment and
// New campaign use, and the host line is Topology's host and Docker nodes.
// Health is an operator state, never a Ground Truth outcome: neutral, accent,
// and amber only, always with a word.

type Level = "ok" | "busy" | "attention" | "off";

interface Signal {
  id: "lane" | "preflight" | "host";
  label: string;
  word: string;
  /** Short context after the label, e.g. "56m ago". */
  meta?: string;
  level: Level;
}

const DOT: Record<Level, string> = {
  ok: "bg-fg-2",
  busy: "bg-accent motion-safe:animate-pulse",
  attention: "bg-warn",
  off: "border border-fg-3",
};

const WORD: Record<Level, string> = {
  ok: "text-fg",
  busy: "text-accent",
  attention: "text-warn",
  off: "text-fg-3",
};

function Dot({ level }: { level: Level }) {
  return <span aria-hidden className={clsx("size-[7px] shrink-0 rounded-full", DOT[level])} />;
}

const levelOf = (health: Health): Level => (HEALTH[health].attention ? "attention" : health === "stopped" || health === "unknown" ? "off" : "ok");

/** Compact age for the corner: "now", "56m", "3h", "2d". */
function shortAgo(ms: number): string {
  const m = Math.round(ms / 60_000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return h < 24 ? `${h}h ago` : `${Math.round(h / 24)}d ago`;
}

function preflightSignal(fresh: Freshness): Signal {
  switch (fresh.state) {
    case "checking":
      return { id: "preflight", label: "Preflight", word: "Checking", level: "busy" };
    case "never":
      return { id: "preflight", label: "Preflight", word: "Not checked", level: "off" };
    case "blocked":
      return { id: "preflight", label: "Preflight", word: "Blocked", meta: shortAgo(fresh.age), level: "attention" };
    case "stale":
      return { id: "preflight", label: "Preflight", word: "Stale", meta: shortAgo(fresh.age), level: "attention" };
    case "fresh":
      return { id: "preflight", label: "Preflight", word: "Ready", meta: `${Math.max(1, Math.ceil(fresh.left / 60_000))}m left`, level: "ok" };
  }
}

/** The host's own warnings: the host and its Docker daemon, not everything they contain. */
function hostOf(graph: TopologyGraph) {
  const host = graph.byId.get("host");
  const docker = graph.byId.get("docker");
  const nodes = [host, docker].filter((n): n is NonNullable<typeof n> => Boolean(n));
  const worst = nodes.reduce<Health>((acc, n) => (HEALTH[n.health].rank < HEALTH[acc].rank ? n.health : acc), "healthy");
  return { host, docker, worst };
}

function useSignals() {
  // Topology's own graph, including a blocked preflight, so the lane line
  // never disagrees with the Topology page.
  const { graph } = useGraph();
  const readiness = useFreshness();

  const signals: Signal[] = [];
  if (graph) {
    const lane = graph.lane;
    signals.push({ id: "lane", label: "Lane", word: HEALTH[lane.health].word, meta: lane.explained.length ? `${lane.explained.length} explained` : undefined, level: levelOf(lane.health) });
  } else {
    signals.push({ id: "lane", label: "Lane", word: "Loading", level: "off" });
  }
  signals.push(preflightSignal(readiness.fresh));
  if (graph) {
    const { worst } = hostOf(graph);
    signals.push({ id: "host", label: "Host", word: HEALTH[worst].word, meta: `${HOST.diskFreeGB} GB free`, level: levelOf(worst) });
  } else {
    signals.push({ id: "host", label: "Host", word: "Loading", level: "off" });
  }
  return { signals, graph, readiness };
}

function summaryLabel(signals: Signal[]): string {
  const attention = signals.filter((s) => s.level === "attention").length;
  const head = attention ? `${attention} need${attention === 1 ? "s" : ""} attention` : signals.some((s) => s.level === "busy") ? "checking" : "nothing needs attention";
  return `System health, demo: ${head}. ${signals.map((s) => `${s.label} ${s.word}${s.meta ? `, ${s.meta}` : ""}`).join("; ")}. Show details`;
}

// ------------------------------------------------------------------ popover

function Section({ children }: { children: ReactNode }) {
  return <section className="grid gap-2 border-b border-line px-4 py-3 last:border-b-0">{children}</section>;
}

function SectionHead({ label, word, level, demo }: { label: ReactNode; word: string; level: Level; demo?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Dot level={level} />
      <span className="min-w-0 truncate text-[13px] font-medium">{label}</span>
      {demo && <Tag tone="accent">Demo</Tag>}
      <span className={clsx("ml-auto shrink-0 text-[12.5px] font-medium", WORD[level])}>{word}</span>
    </div>
  );
}

function GoLink({ to, children, onGo }: { to: string; children: ReactNode; onGo: () => void }) {
  return (
    <Link to={to} onClick={onGo} className="inline-flex items-center gap-1 rounded-sm text-[12px] text-fg-2 hover:text-fg">
      {children} <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
    </Link>
  );
}

function NodeChips({ graph, ids, tone, onGo }: { graph: TopologyGraph; ids: string[]; tone: "warn" | "neutral"; onGo: () => void }) {
  const shown = ids.slice(0, 6);
  return (
    <ul className="flex flex-wrap gap-1">
      {shown.map((id) => {
        const node = graph.byId.get(id);
        if (!node) return null;
        return (
          <li key={id} className="min-w-0 max-w-full">
            <Link
              to={`/lab/topology?node=${encodeURIComponent(id)}`}
              onClick={onGo}
              title={`${node.name}: ${HEALTH[node.health].word}`}
              className={clsx(
                "inline-flex h-6 max-w-full items-center gap-1.5 rounded-md border px-1.5 text-[11.5px] hover:bg-surface-2",
                tone === "warn" ? "border-warn/40 text-warn" : "border-line text-fg-2",
              )}
            >
              <span className="ident truncate">{node.name}</span>
              <span className="shrink-0 text-fg-3">{HEALTH[node.health].word.toLowerCase()}</span>
            </Link>
          </li>
        );
      })}
      {ids.length > shown.length && <li className="self-center text-[11.5px] text-fg-3">+{ids.length - shown.length} more</li>}
    </ul>
  );
}

function Details({ signals, graph, readiness, onGo }: { signals: Signal[]; graph?: TopologyGraph; readiness: ReturnType<typeof useFreshness>; onGo: () => void }) {
  const runs = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const { data: generatedAt } = useQuery({ queryKey: ["snapshot-date"], queryFn: snapshotGeneratedAt });
  const [lane, preflight, host] = signals;
  const attention = signals.filter((s) => s.level === "attention").length;
  const fresh = readiness.fresh;
  const latest = fresh.state === "never" ? undefined : fresh.latest;
  const groups = latest ? groupChecks(latest.checks) : [];
  const hostNodes = graph ? hostOf(graph) : undefined;

  return (
    <div className="grid">
      <header className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="label !text-[10px]">System health</span>
        <span className={clsx("ml-auto text-[12px] font-medium", attention ? "text-warn" : "text-fg-2")}>
          {attention ? `${attention} need${attention === 1 ? "s" : ""} attention` : "Nothing needs attention"}
        </span>
      </header>

      <Section>
        <SectionHead label={<>Lane <span className="ident text-fg-2">minh</span></>} word={lane.word} level={lane.level} demo />
        {graph && (
          <>
            <p className="text-[12px] leading-relaxed text-fg-3">{graph.lane.reason}</p>
            {graph.lane.attention.length > 0 && <NodeChips graph={graph} ids={graph.lane.attention} tone="warn" onGo={onGo} />}
            {graph.lane.explained.length > 0 && (
              <div className="grid gap-1">
                <span className="text-[11.5px] text-fg-3">Explained, not counted</span>
                <NodeChips graph={graph} ids={graph.lane.explained} tone="neutral" onGo={onGo} />
              </div>
            )}
          </>
        )}
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <GoLink to="/lab/topology" onGo={onGo}>
            Open topology
          </GoLink>
        </div>
      </Section>

      <Section>
        <SectionHead label="Preflight" word={preflight.word} level={preflight.level} demo />
        <p className="text-[12px] leading-relaxed text-fg-3">{freshnessLine(fresh)}</p>
        {groups.length > 0 && (
          <ul className="grid grid-cols-2 gap-x-3 gap-y-1" aria-label={latest ? `Check groups in the ${stamp(latest.finishedAt)} UTC result` : "Check groups"}>
            {groups.map((group) => (
              <li key={group.id} className="flex min-w-0 items-center gap-1.5 text-[12px]" title={`${group.label}: ${group.worst ? LEVEL_WORD[group.worst] : "No result"}`}>
                <CheckMark level={group.worst} />
                <span className={clsx("truncate", group.worst === "warn" || group.worst === "block" ? "text-warn" : "text-fg-2")}>{group.label}</span>
                <span className="sr-only">{group.worst ? LEVEL_WORD[group.worst] : "No result"}</span>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <GoLink to="/environment" onGo={onGo}>
            Open environment
          </GoLink>
        </div>
      </Section>

      <Section>
        <SectionHead label="Lab host" word={host.word} level={host.level} demo />
        {hostNodes?.docker && <p className="text-[12px] leading-relaxed text-fg-3">{hostNodes.docker.reason}</p>}
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <GoLink to="/lab" onGo={onGo}>
            Open resources
          </GoLink>
          <GoLink to="/lab/topology?node=docker" onGo={onGo}>
            Docker in topology
          </GoLink>
        </div>
      </Section>

      <Section>
        <SectionHead label="Data" word={api.source.label} level="ok" />
        <p className="text-[12px] leading-relaxed text-fg-3">
          {api.source.mode === "fixture" ? (
            <>
              {runs.data ? `${runs.data.length} recorded runs` : "Recorded runs"} from <span className="ident">data/</span>
              {generatedAt ? `, snapshot taken ${stamp(Date.parse(generatedAt))} UTC` : ""}. Real results; only the live views are simulated.
            </>
          ) : (
            <>{runs.data ? `${runs.data.length} recorded runs` : "Recorded runs"} from the operator backend.</>
          )}
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <GoLink to="/runs" onGo={onGo}>
            Open runs
          </GoLink>
        </div>
      </Section>
    </div>
  );
}

// ------------------------------------------------------------------ corner

/**
 * The sidebar corner card. `side` places the popover: to the right of the
 * desktop sidebar, above the card inside the phone navigation drawer.
 * `onNavigate` closes the drawer when a link is followed.
 */
function FixtureSystemHealth({ side = "right", onNavigate }: { side?: "right" | "top"; onNavigate?: () => void }) {
  const { signals, graph, readiness } = useSignals();
  const [open, setOpen] = useState(false);
  const go = () => {
    setOpen(false);
    onNavigate?.();
  };

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label={summaryLabel(signals)}
          className="group mx-3 mb-3 grid cursor-pointer gap-1.5 rounded-md border border-line px-3 py-2.5 text-left transition-colors hover:border-line-strong hover:bg-surface-2/60 data-[state=open]:border-line-strong data-[state=open]:bg-surface-2"
        >
          <span className="flex items-center gap-2">
            <span className="label !text-[10px]">Health</span>
            <Tag tone="accent" className="!h-4 !px-1 !text-[9.5px]">
              Demo
            </Tag>
            <ChevronRight className="ml-auto size-3.5 text-fg-3 transition-transform group-data-[state=open]:translate-x-0.5" strokeWidth={1.75} aria-hidden />
          </span>
          <span className="grid grid-cols-[7px_minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1">
            {signals.map((signal) => (
              <span key={signal.id} className="contents">
                <Dot level={signal.level} />
                <span className="min-w-0 truncate text-[12px]">
                  <span className="text-fg-2">{signal.label}</span>
                  {signal.meta && <span className="text-fg-3"> · {signal.meta}</span>}
                </span>
                <span className={clsx("text-[12px] font-medium whitespace-nowrap", WORD[signal.level])}>{signal.word}</span>
              </span>
            ))}
          </span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side={side}
          align={side === "right" ? "end" : "center"}
          sideOffset={side === "right" ? 12 : 8}
          collisionPadding={12}
          tabIndex={-1}
          aria-label="System health"
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            (event.currentTarget as HTMLElement | null)?.focus?.();
          }}
          className="z-[60] max-h-[var(--radix-popover-content-available-height)] w-[min(360px,calc(100vw-24px))] overflow-y-auto rounded-lg border border-line bg-surface shadow-pop outline-none"
        >
          <Details signals={signals} graph={graph} readiness={readiness} onGo={go} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function ApiSystemHealth({ side = "right", onNavigate }: { side?: "right" | "top"; onNavigate?: () => void }) {
  const topology = useQuery({ queryKey: ["topology"], queryFn: api.topology, refetchInterval: 5_000, staleTime: 0, retry: 0 });
  const telemetry = useQuery({ queryKey: ["telemetry"], queryFn: api.telemetry, refetchInterval: 2_000, staleTime: 0, retry: 0 });
  const jobsQuery = useQuery({ queryKey: ["operator-jobs"], queryFn: api.jobs, refetchInterval: 1_500, staleTime: 0, retry: 0 });
  const overviewQuery = useQuery({ queryKey: ["operator-overview"], queryFn: api.overview, refetchInterval: 10_000, staleTime: 0, retry: 0 });
  const [open, setOpen] = useState(false);
  const go = () => { setOpen(false); onNavigate?.(); };
  const jobs = [...(jobsQuery.data ?? [])].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const active = jobs.find((job) => ["queued", "running", "stop_requested"].includes(job.status));
  const selected = (topology.data as TopologySnapshot | undefined)?.selected_profile;
  const sample = telemetry.data as TelemetrySample | undefined;
  const topologySnapshot = topology.data as TopologySnapshot | undefined;
  const laneLevel: Level = topology.error || !selected || selected.status.toLowerCase() === "unknown" ? "off" : topologySnapshot?.stale || topologySnapshot?.status === "stale" ? "attention" : selected.status.toLowerCase() === "running" ? "ok" : "attention";
  const laneWord = topology.error || !selected ? "Unavailable" : topologySnapshot?.stale || topologySnapshot?.status === "stale" ? "Stale" : selected.status;
  const readinessSnapshot = overviewQuery.data?.readiness;
  const readiness = jobsQuery.error || overviewQuery.error ? { word: "Unavailable", level: "off" as Level }
    : active?.kind === "readiness" || active?.kind === "prepare" ? { word: "Checking", level: "busy" as Level }
      : readinessSnapshot?.status === "BLOCKED" ? readinessSnapshot.fresh ? { word: "Blocked", level: "attention" as Level } : { word: "Stale", level: "attention" as Level }
        : readinessSnapshot?.status === "READY" && readinessSnapshot.ready ? { word: "Ready", level: "ok" as Level }
          : readinessSnapshot?.status === "READY" ? { word: "Stale", level: "attention" as Level }
            : { word: "Not checked", level: "off" as Level };
  const hostLevel: Level = telemetry.error || sample?.status === "unavailable" ? "off" : sample?.stale || sample?.status === "stale" ? "attention" : sample ? "ok" : "off";
  const hostWord = telemetry.error ? "Unavailable" : sample?.status === "unavailable" ? "Unavailable" : sample?.stale || sample?.status === "stale" ? "Stale" : sample ? "Live" : "Loading";
  const signals: Signal[] = [
    { id: "lane", label: "Lane", word: laneWord, meta: selected?.name, level: laneLevel },
    { id: "preflight", label: "Preflight", word: readiness.word, level: readiness.level },
    { id: "host", label: "Host", word: hostWord, meta: sample?.sampled_at ? shortAgo(Date.now() - Date.parse(sample.sampled_at)) : undefined, level: hostLevel },
  ];
  const attention = signals.filter((signal) => signal.level === "attention").length;
  const summary = `System health: ${attention ? `${attention} need${attention === 1 ? "s" : ""} attention` : "no reported attention"}. ${signals.map((signal) => `${signal.label} ${signal.word}`).join("; ")}. Show details`;
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button type="button" aria-label={summary} className="group mx-3 mb-3 grid cursor-pointer gap-1.5 rounded-md border border-line px-3 py-2.5 text-left transition-colors hover:border-line-strong hover:bg-surface-2/60 data-[state=open]:border-line-strong data-[state=open]:bg-surface-2">
          <span className="flex items-center gap-2"><span className="label !text-[10px]">Health</span><Tag tone="neutral">Live</Tag><ChevronRight className="ml-auto size-3.5 text-fg-3" strokeWidth={1.75} aria-hidden /></span>
          <span className="grid grid-cols-[7px_minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1">{signals.map((signal) => <span key={signal.id} className="contents"><Dot level={signal.level} /><span className="min-w-0 truncate text-[12px]"><span className="text-fg-2">{signal.label}</span>{signal.meta && <span className="text-fg-3"> · {signal.meta}</span>}</span><span className={clsx("text-[12px] font-medium whitespace-nowrap", WORD[signal.level])}>{signal.word}</span></span>)}</span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content side={side} align={side === "right" ? "end" : "center"} sideOffset={side === "right" ? 12 : 8} collisionPadding={12} aria-label="Live system health" className="z-[60] max-h-[var(--radix-popover-content-available-height)] w-[min(360px,calc(100vw-24px))] overflow-y-auto rounded-lg border border-line bg-surface shadow-pop outline-none">
          <div className="grid">
            <header className="flex items-center gap-2 border-b border-line px-4 py-3"><span className="label !text-[10px]">System health</span><span className="ml-auto text-[12px] text-fg-3">{api.source.label}</span></header>
            <section className="grid gap-2 border-b border-line px-4 py-3"><div className="flex items-center gap-2"><Dot level={laneLevel} /><span className="text-[13px] font-medium">Selected lane</span><span className={clsx("ml-auto text-[12.5px] font-medium", WORD[laneLevel])}>{laneWord}</span></div>{topology.error ? <p className="text-[12px] text-fg-3">Topology unavailable: {topology.error.message}</p> : selected ? <><p className="ident text-[12px] text-fg-2">{selected.name}</p><p className="text-[12px] text-fg-3">{selected.nodes.length} nodes · {selected.pods == null ? "pod inventory unavailable" : `${selected.pods.length} pods in the selected lane`}</p></> : <p className="text-[12px] text-fg-3">Selected lane inventory is unavailable.</p>}<Link to="/lab/topology" onClick={go} className="inline-flex w-fit items-center gap-1 text-[12px] text-fg-2 hover:text-fg">Open topology <ArrowUpRight className="size-3.5" /></Link></section>
            <section className="grid gap-2 border-b border-line px-4 py-3"><div className="flex items-center gap-2"><Dot level={readiness.level} /><span className="text-[13px] font-medium">Preflight</span><span className={clsx("ml-auto text-[12.5px] font-medium", WORD[readiness.level])}>{readiness.word}</span></div>{readinessSnapshot?.checked_at && <p className="num text-[12px] text-fg-3">Checked {new Date(readinessSnapshot.checked_at).toLocaleString()}{!readinessSnapshot.fresh ? ` · ${readinessSnapshot.reason?.replaceAll("_", " ") ?? "stale"}` : ""}</p>}{active && <p className="text-[12px] text-fg-3">{active.kind === "prepare" ? "Preparation" : active.kind === "readiness" ? "Preflight" : "Operator job"} is {active.status}.</p>}<Link to="/environment" onClick={go} className="inline-flex w-fit items-center gap-1 text-[12px] text-fg-2 hover:text-fg">Open environment <ArrowUpRight className="size-3.5" /></Link></section>
            <section className="grid gap-2 border-b border-line px-4 py-3 last:border-b-0"><div className="flex items-center gap-2"><Dot level={hostLevel} /><span className="text-[13px] font-medium">Host telemetry</span><span className={clsx("ml-auto text-[12.5px] font-medium", WORD[hostLevel])}>{hostWord}</span></div>{sample?.sampled_at && <p className="num text-[12px] text-fg-3">Sampled {new Date(sample.sampled_at).toLocaleString()}{sample.stale ? " · stale" : ""}</p>}{telemetry.error && <p className="text-[12px] text-fg-3">Telemetry unavailable: {telemetry.error.message}</p>}<Link to="/lab" onClick={go} className="inline-flex w-fit items-center gap-1 text-[12px] text-fg-2 hover:text-fg">Open resources <ArrowUpRight className="size-3.5" /></Link></section>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

export default function SystemHealth(props: { side?: "right" | "top"; onNavigate?: () => void }) {
  return api.isLive ? <ApiSystemHealth {...props} /> : <FixtureSystemHealth {...props} />;
}
