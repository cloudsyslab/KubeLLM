import clsx from "clsx";
import { ChartGantt, ListTree, Radio } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { Segmented } from "@/components/ui";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { graphAt, phaseColumns, whatIf } from "@/demo/topologyGraph";
import { StageFallback } from "../OptionsRoom";
import { MomentHeader, TimelineView } from "./HealthTimeline";
import { DemoTag, Inspector, LaneHealth, TrafficLine, useGraph } from "./shared";
import { MapView } from "./StructuredMap";

// Topology: the structured map (host, then the lane) or the health timeline,
// beside one explanation panel. Selection, the simulated failure, and the
// trail of explained components are shared, so a component picked in either
// view is explained the same way. The URL carries the view (?view=timeline)
// and the selected component (?node=docker), so other pages can link to one.

type View = "map" | "timeline";
const DEFAULT_NODE = "profile:minh-lane";

export default function TopologyExplorer() {
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
