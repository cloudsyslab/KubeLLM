import clsx from "clsx";
import { ChartGantt, ListTree, Radio } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { api } from "@/api/client";
import type { CampaignHealthHistory } from "@/api/types";
import { Segmented, Tag } from "@/components/ui";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { graphAt, phaseColumns, whatIf } from "@/demo/topologyGraph";
import { StageFallback } from "../OptionsRoom";
import { MomentHeader, TimelineView } from "./HealthTimeline";
import { DemoTag, HEALTH_SHORT, HEALTH_TEXT, HealthMark, Inspector, Inspector as LiveInspector, LaneHealth, LaneHealth as LiveLaneHealth, TrafficLine, TrafficLine as LiveTrafficLine, useGraph } from "./shared";
import { MapView } from "./StructuredMap";
import { buildLiveGraph } from "./liveGraph";

// Topology: the structured map (host, then the lane) or the health timeline,
// beside one explanation panel. Selection, the simulated failure, and the
// trail of explained components are shared, so a component picked in either
// view is explained the same way. The URL carries the view (?view=timeline)
// and the selected component (?node=docker), so other pages can link to one.

type View = "map" | "timeline";
const DEFAULT_NODE = "profile:minh-lane";

function ReplayTopologyExplorer() {
  const { graph, campaign } = useGraph();
  const { t } = useReplay();
  const [params, setParams] = useSearchParams();
  const view: View = params.get("view") === "timeline" ? "timeline" : "map";
  const nodeParam = params.get("node");
  const [trail, setTrail] = useState<string[]>(() => [nodeParam ?? DEFAULT_NODE]);
  const [whatIfOn, setWhatIfOn] = useState(false);
  const [col, setCol] = useState<number | null>(null);
  const selected = trail[trail.length - 1];

  const setParam = useCallback(
    (key: string, value: string | null) =>
      setParams(
        (current) => {
          const out = new URLSearchParams(current);
          if (value === null) out.delete(key);
          else out.set(key, value);
          return out;
        },
        { replace: true },
      ),
    [setParams],
  );
  const setView = (next: View) => setParam("view", next === "map" ? null : next);

  const select = useCallback((id: string) => setTrail((h) => (h[h.length - 1] === id ? h : [...h.slice(-11), id])), []);

  // A link that changes ?node= selects that component; selecting one keeps
  // ?node= in step, so the address always names what the panel explains.
  useEffect(() => {
    if (nodeParam && nodeParam !== selected) select(nodeParam);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- follow the link only
  }, [nodeParam]);
  useEffect(() => {
    if (nodeParam !== selected && (nodeParam || selected !== DEFAULT_NODE)) setParam("node", selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- follow the selection only
  }, [selected]);

  // Phase columns are only needed once the timeline has been opened.
  const [timelineOpened, setTimelineOpened] = useState(view === "timeline");
  if (view === "timeline" && !timelineOpened) setTimelineOpened(true);
  const columns = useMemo(() => (campaign && timelineOpened ? phaseColumns(campaign) : []), [campaign, timelineOpened]);
  const pinned = view === "timeline" && col !== null ? columns[col] : undefined;
  const pinnedGraph = useMemo(() => (campaign && pinned ? graphAt(campaign, (pinned.phase.start + pinned.phase.end) / 2) : undefined), [campaign, pinned]);
  const shown = pinnedGraph ?? graph;
  const impact = useMemo(() => (shown && whatIfOn && shown.byId.has(selected) ? whatIf(shown, selected) : undefined), [shown, whatIfOn, selected]);

  if (!graph || !shown || !campaign) return <StageFallback />;

  const previous = trail.length > 1 ? trail[trail.length - 2] : undefined;
  const panel = (
    <Inspector
      graph={shown}
      id={selected}
      onSelect={select}
      whatIfOn={whatIfOn}
      onWhatIf={setWhatIfOn}
      impact={impact}
      back={previous ? { name: shown.byId.get(previous)?.name ?? graph.byId.get(previous)?.name ?? previous, onBack: () => setTrail((h) => h.slice(0, -1)) } : undefined}
      header={
        pinned ? (
          <MomentHeader column={pinned} onNow={() => setCol(null)} />
        ) : (
          <div className="label inline-flex items-center gap-1.5 !text-[10px]">
            <Radio className="size-3 text-accent" strokeWidth={2} /> Now · {clock(t)}
          </div>
        )
      }
    />
  );

  return (
    <div className="grid gap-3">
      <div className="grid gap-2 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <DemoTag />
          <LaneHealth graph={graph} />
          <span className="hidden text-[12.5px] text-fg-3 lg:inline">
            Default kubectl context <span className="font-mono text-fg-2">minikube</span> · never used to pick a target
          </span>
          <div className="ml-auto">
            <Segmented
              label="View"
              value={view}
              onChange={setView}
              options={[
                { value: "map", label: <><ListTree className="size-3.5" strokeWidth={1.75} aria-hidden /> Map</>, hint: "The containment tree: host, then the lane" },
                { value: "timeline", label: <><ChartGantt className="size-3.5" strokeWidth={1.75} aria-hidden /> Timeline</>, hint: "Each component's health at every phase of the campaign" },
              ]}
            />
          </div>
        </div>
        <TrafficLine graph={graph} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {view === "map" ? (
          <MapView
            graph={graph}
            selected={selected}
            onSelect={select}
            impact={impact}
            onToggleWhatIf={() => setWhatIfOn((on) => !on)}
            onWhatIfOff={() => setWhatIfOn(false)}
            panel={panel}
          />
        ) : (
          <TimelineView
            graph={graph}
            columns={columns}
            selected={selected}
            col={col}
            onSelect={(id, at) => {
              select(id);
              setCol(at);
            }}
            onToggleWhatIf={() => setWhatIfOn((on) => !on)}
          />
        )}
        <aside
          aria-label="Explanation"
          className={clsx(
            "min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface xl:sticky xl:top-20 xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto",
            view === "map" && "hidden xl:block",
          )}
        >
          {panel}
        </aside>
      </div>
      <p className="text-[12px] leading-relaxed text-fg-3">
        Demo state shaped by the lab survey (Nov 1, 2026). Health is the lab's state, not a benchmark outcome: containers summarize their contents, and fixtures broken by design and known leftovers are explained, never counted against the lane. The timeline samples each phase at its midpoint. On the map, arrow keys move between rows and W shows what fails.
      </p>
    </div>
  );
}

const HISTORY_COLUMNS = 30;

function LiveHealthTimeline({ samples, graph, selected, onSelect, selectedSample, onSelectSample, truncated }: {
  samples: CampaignHealthHistory["samples"];
  graph: ReturnType<typeof buildLiveGraph>;
  selected: string;
  onSelect: (id: string, index: number) => void;
  selectedSample: number | null;
  onSelectSample: (index: number | null) => void;
  truncated: boolean;
}) {
  const visible = samples.slice(-HISTORY_COLUMNS);
  const firstVisible = samples.length - visible.length;
  const sampleGraphs = useMemo(() => visible.map((sample) => ({ at: sample.sampled_at, graph: buildLiveGraph(sample.topology, sample.telemetry) })), [visible]);
  const rows = graph.nodes;
  const look: Record<string, string> = {
    healthy: "bg-fg/25",
    degraded: "bg-warn/55",
    failing: "bg-warn",
    stopped: "after:absolute after:inset-x-0 after:top-1/2 after:h-0.5 after:-translate-y-1/2 after:bg-fg-3/45",
    unknown: "after:absolute after:inset-x-0 after:top-1/2 after:h-px after:-translate-y-1/2 after:bg-fg-3/35",
    leftover: "bg-warn/25",
    "expected-broken": "hatch bg-fg/10",
  };
  if (!visible.length) return <section className="grid gap-2 rounded-lg border border-line bg-surface p-4"><h3 className="text-[13px] font-medium">Campaign health history</h3><p className="text-[12.5px] text-fg-3">No health observations were retained for this campaign. The operator samples at campaign start and about every 30 seconds while the selected lane stays the same; a short campaign may finish before its first sample is stored.</p></section>;
  return (
    <section className="grid gap-3 overflow-hidden rounded-lg border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3"><h3 className="text-[13px] font-medium">Campaign health history</h3><span className="text-[12px] text-fg-3">Each column is a recorded observation; no phase states are inferred.</span>{truncated && <Tag tone="warn">Older samples trimmed</Tag>}</div>
      {firstVisible > 0 && <p className="text-[11.5px] text-fg-3">Showing the latest {visible.length} of {samples.length} retained observations.</p>}
      <div className="overflow-x-auto"><div className="min-w-max">
        <div className="grid grid-cols-[220px_minmax(0,1fr)] items-end gap-3 border-b border-line pb-2">
          <span className="label !text-[10px]">Component</span>
          <div className="flex min-w-0 gap-[3px]">{visible.map((sample, index) => <button key={`${sample.sampled_at}-${index}`} type="button" onClick={() => onSelectSample(index + firstVisible)} aria-pressed={selectedSample === index + firstVisible} title={new Date(sample.sampled_at).toLocaleString()} className={clsx("min-w-3 flex-1 rounded-t-sm border-b-2 px-1 pb-1 text-center font-mono text-[9px] text-fg-3 hover:text-fg", selectedSample === index + firstVisible ? "border-accent text-fg" : "border-line")}>{new Date(sample.sampled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</button>)}</div>
        </div>
        <div className="grid gap-1 pt-2">{rows.map((item) => <div key={item.id} className="grid grid-cols-[220px_minmax(0,1fr)] items-center gap-3">
          <button type="button" onClick={() => onSelect(item.id, selectedSample ?? Math.max(0, visible.length - 1) + firstVisible)} className={clsx("flex min-w-0 items-center gap-2 truncate rounded px-1 py-1 text-left text-[11.5px] hover:bg-surface-2", selected === item.id && "bg-accent-soft text-fg")}><HealthMark health={item.health} size={9} /><span className="truncate">{item.name}</span></button>
          <div className="flex min-w-0 gap-[3px]">{sampleGraphs.map((column, index) => {
            const old = column.graph.byId.get(item.id);
            const health = old?.health ?? "unknown";
            const at = index + firstVisible;
            return <button key={`${item.id}-${column.at}`} type="button" aria-label={`${item.name}: ${HEALTH_SHORT[health]} at ${new Date(column.at).toLocaleString()}`} aria-pressed={selectedSample === at && selected === item.id} onClick={() => onSelect(item.id, at)} title={`${new Date(column.at).toLocaleString()} · ${old?.status ?? "Not present in this observation"}`} className={clsx("relative h-5 min-w-3 flex-1 rounded-[2px] outline-offset-1", look[health], selectedSample === at && selected === item.id && "outline outline-1 outline-fg")} />;
          })}</div>
        </div>)}</div>
      </div></div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-fg-3">{(["healthy", "degraded", "failing", "stopped", "unknown"] as const).map((health) => <span key={health} className={clsx("inline-flex items-center gap-1.5", HEALTH_TEXT[health])}><HealthMark health={health} size={9} />{HEALTH_SHORT[health]}</span>)}</div>
    </section>
  );
}

function LiveTopologyExplorer() {
  const [params, setParams] = useSearchParams();
  const topology = useQuery({ queryKey: ["topology"], queryFn: api.topology, refetchInterval: 5_000, staleTime: 0, retry: 0 });
  const telemetry = useQuery({ queryKey: ["telemetry"], queryFn: api.telemetry, refetchInterval: 2_000, staleTime: 0, retry: 0 });
  const jobs = useQuery({ queryKey: ["operator-jobs"], queryFn: api.jobs, refetchInterval: 5_000, staleTime: 0, retry: 0 });
  const campaigns = [...(jobs.data ?? [])].filter((job) => job.kind === "campaign").sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const campaign = campaigns.find((job) => job.id === params.get("campaign")) ?? campaigns[0];
  const history = useQuery({
    queryKey: ["topology-history", campaign?.id],
    queryFn: () => api.topologyHistory(campaign!.id),
    enabled: Boolean(campaign),
    refetchInterval: 5_000,
    staleTime: 0,
    retry: 0,
  });
  const snapshot = topology.data;
  const graph = useMemo(() => snapshot ? buildLiveGraph(snapshot, telemetry.data) : undefined, [snapshot, telemetry.data]);
  const samples = history.data?.samples ?? [];
  const sampleGraphs = useMemo(() => samples.map((sample) => buildLiveGraph(sample.topology, sample.telemetry)), [samples]);
  const mode: View = params.get("view") === "timeline" ? "timeline" : "map";
  const requestedSample = Number(params.get("sample"));
  const selectedSample = mode === "timeline" && Number.isInteger(requestedSample) && requestedSample >= 0 && requestedSample < samples.length ? requestedSample : null;
  const shown = selectedSample == null ? graph : sampleGraphs[selectedSample] ?? graph;
  const defaultNode = graph?.nodes.find((node) => node.kind === "profile" && node.tags.includes("selected-lane"))?.id ?? "host";
  const requestedNode = params.get("node");
  const selected = shown?.byId.has(requestedNode ?? "") ? requestedNode! : defaultNode;
  const updateParams = useCallback((updates: Record<string, string | null>) => setParams((current) => {
    const next = new URLSearchParams(current);
    for (const [key, value] of Object.entries(updates)) {
      if (value == null) next.delete(key); else next.set(key, value);
    }
    return next;
  }, { replace: true }), [setParams]);
  useEffect(() => {
    if (selected !== requestedNode) updateParams({ node: selected });
  }, [selected, requestedNode, updateParams]);
  useEffect(() => {
    if (campaign && campaign.id !== params.get("campaign")) updateParams({ campaign: campaign.id });
  }, [campaign?.id, params, updateParams]);
  const setView = (next: View) => {
    updateParams({ view: next === "map" ? null : next, ...(next === "map" ? { sample: null } : {}) });
  };
  const chooseCampaign = (id: string) => {
    updateParams({ campaign: id || null, sample: null });
  };
  const select = (id: string, sampleIndex?: number) => {
    updateParams({ node: id, ...(sampleIndex != null ? { sample: String(sampleIndex) } : {}) });
  };
  const shownAt = selectedSample == null ? snapshot?.sampled_at : samples[selectedSample]?.sampled_at;
  const panel = shown && <LiveInspector
    graph={shown}
    id={selected}
    onSelect={(id) => select(id)}
    whatIfOn={false}
    onWhatIf={() => undefined}
    header={<div className="label inline-flex items-center gap-1.5 !text-[10px]"><Radio className="size-3 text-accent" strokeWidth={2} />{selectedSample == null ? "Latest read" : "Recorded sample"}{shownAt ? ` · ${new Date(shownAt).toLocaleString()}` : ""}</div>}
  />;

  if (topology.isError) return <p className="rounded-lg border border-warn/40 bg-warn-soft px-4 py-3 text-[12.5px] text-warn">Topology unavailable: {topology.error.message}</p>;
  if (!snapshot || !graph || !shown || !panel) return <div className="h-48 animate-pulse rounded-lg bg-surface" />;
  return (
    <div className="grid gap-3">
      <div className="grid gap-2 rounded-lg border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2"><Tag tone={snapshot.status === "unavailable" || snapshot.status === "partial" || snapshot.stale ? "warn" : "neutral"}>{snapshot.status === "unavailable" ? "Unavailable" : snapshot.status === "partial" ? "Partial sample" : snapshot.stale ? "Stale sample" : "Live inventory"}</Tag><span className="num text-[11.5px] text-fg-3">{new Date(snapshot.sampled_at).toLocaleString()}</span><LiveLaneHealth graph={graph} />
          <div className="ml-auto flex flex-wrap items-center gap-3"><label className="flex items-center gap-2 text-[12px] text-fg-3"><span>Campaign history</span><select value={campaign?.id ?? ""} onChange={(event) => chooseCampaign(event.target.value)} className="max-w-64 rounded border border-line bg-surface px-2 py-1 text-fg" aria-label="Campaign health history">{!campaigns.length && <option value="">No campaigns recorded</option>}{campaigns.map((item) => <option key={item.id} value={item.id}>{item.status} · {new Date(item.created_at).toLocaleString()}</option>)}</select></label><Segmented label="View" value={mode} onChange={setView} options={[{ value: "map", label: <><ListTree className="size-3.5" strokeWidth={1.75} aria-hidden /> Map</>, hint: "Current read-only containment inventory" }, { value: "timeline", label: <><ChartGantt className="size-3.5" strokeWidth={1.75} aria-hidden /> Timeline</>, hint: "Recorded health observations for this campaign" }]} /></div>
        </div>
        {snapshot.reason && <p className="text-[12px] text-fg-3">{snapshot.reason}</p>}
        {history.error && <p className="text-[12px] text-warn">Campaign health history unavailable: {history.error.message}</p>}
        {history.data?.reason === "lane_changed" && <p className="text-[12px] text-warn">This campaign belongs to a different selected-lane fingerprint. Its health history is hidden.</p>}
        <LiveTrafficLine graph={graph} />
      </div>
      {mode === "map" ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]"><MapView graph={graph} selected={selected} onSelect={(id) => select(id)} onToggleWhatIf={() => undefined} onWhatIfOff={() => undefined} panel={panel} allowWhatIf={false} /><aside aria-label="Explanation" className="min-w-0 self-start overflow-hidden rounded-lg border border-line bg-surface xl:sticky xl:top-20 xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto">{panel}</aside></div>
      ) : (
        <LiveHealthTimeline samples={samples} graph={graph} selected={selected} onSelect={select} selectedSample={selectedSample} onSelectSample={(index) => updateParams({ sample: index == null ? null : String(index) })} truncated={history.data?.truncated ?? false} />
      )}
      <p className="text-[12px] leading-relaxed text-fg-3">The live map uses reported containment from the selected kubeconfig, host telemetry, and configured lane services. Dependency links are not available in this inventory. Timeline columns are persisted observations taken during campaigns; missing periods remain unknown.</p>
    </div>
  );
}

export default function TopologyExplorer() {
  return api.isLive ? <LiveTopologyExplorer /> : <ReplayTopologyExplorer />;
}
