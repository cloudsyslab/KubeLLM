import { useMemo, useState } from "react";
import { Scatter, ScatterChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { ScatterPointItem, TooltipValueType } from "recharts";
import { Activity, ArrowDownWideNarrow, ArrowUpRight, ChevronDown, CircleDot, Command, Cpu, Database, Gauge, HardDrive, Layers3, MemoryStick, Radio, Search, Server, ShieldAlert, ShieldCheck, Terminal, Timer, TriangleAlert, Workflow } from "lucide-react";
import type { DirectionProps, MetricId, ModelScore, Tone } from "../domain";
import { cases, events, formatDollars, formatRate, illustrativeNotice, models, profiles, resources } from "../data";
import { CaseMatrix, DemoBanner, HostTrendChart, JobSummary, LabelCell, LabTopology, MetricSummary, MiniTerminal, PageHeading, Panel, Pill, ProgressMeter, ResourceChart, ResourceTiles, SearchBox, StepTimeline, TraceTable } from "../shared";
import "./Signal.css";

const metricName: Record<MetricId, string> = { success: "success", cost: "cost / attempt", speed: "seconds / attempt" };

function formatScatterTooltip(value: TooltipValueType | undefined, name: string | number | undefined): [string, string] {
  const label = String(name ?? "");
  const raw = Array.isArray(value) ? value.join(", ") : value;
  const display = label.toLowerCase().includes("success")
    ? `${raw ?? "—"}%`
    : label.toLowerCase().includes("cost")
      ? `$${Number(raw).toFixed(2)}`
      : `${raw ?? "—"}s`;
  return [display, label];
}

function formatMetric(model: ModelScore, metric: MetricId) {
  if (metric === "success") return formatRate(model.success);
  if (metric === "cost") return formatDollars(model.cost);
  return `${model.speed.toFixed(1)}s`;
}

function toneForScore(score: number): Tone {
  return score >= 80 ? "good" : score >= 60 ? "warn" : "bad";
}

function HostStrip() {
  return <div className="signal-host-strip"><span className="signal-node-name"><i className="signal-live-dot" /> LAB HOST <b>2 × A40</b></span><span><Cpu size={13} /> CPU <b>68%</b><i className="signal-mini-bar"><i style={{ width: "68%" }} /></i></span><span><MemoryStick size={13} /> RAM <b>58%</b><i className="signal-mini-bar signal-mini-amber"><i style={{ width: "58%" }} /></i></span><span><Gauge size={13} /> GPU <b>82%</b><i className="signal-mini-bar signal-mini-gpu"><i style={{ width: "82%" }} /></i></span><span className="signal-strip-time"><Radio size={12} /> sample · 1s</span></div>;
}

function Navigation({ page, onPageChange }: Pick<DirectionProps, "page" | "onPageChange">) {
  const items = [{ id: "explorer" as const, label: "Eval explorer", icon: <Activity size={15} /> }, { id: "execution" as const, label: "Job execution", icon: <Terminal size={15} /> }, { id: "lab" as const, label: "Lab topology", icon: <Workflow size={15} /> }];
  return <nav className="signal-nav" aria-label="Signal workspace">{items.map((item) => <button key={item.id} className={page === item.id ? "signal-nav-active" : ""} onClick={() => onPageChange(item.id)}>{item.icon}<span>{item.label}</span>{item.id === "execution" && <i className="signal-nav-pulse" />}</button>)}<div className="signal-nav-spacer" /><span className="signal-nav-footer"><ShieldCheck size={13} /> selected lane · actions gated</span></nav>;
}

function MetricTabs({ metric, onChange }: { metric: MetricId; onChange: (metric: MetricId) => void }) {
  return <div className="signal-metric-tabs" role="group" aria-label="Primary leaderboard metric">{(["success", "cost", "speed"] as MetricId[]).map((value) => <button key={value} className={metric === value ? "selected" : ""} onClick={() => onChange(value)}>{value === "success" ? <ShieldCheck size={13} /> : value === "cost" ? <Database size={13} /> : <Timer size={13} />}{value === "success" ? "Success" : value === "cost" ? "Lowest cost" : "Fastest"}</button>)}</div>;
}

function ScoreScatter({ metric, selectedModelId, onModelSelect }: Pick<DirectionProps, "metric" | "selectedModelId" | "onModelSelect">) {
  const xMetric = metric === "speed" ? "seconds / attempt (lower is faster)" : metric === "cost" ? "cost / attempt (lower is cheaper)" : "cost / attempt (lower is cheaper)";
  const plotted = useMemo(() => models.map((model) => ({ x: metric === "speed" ? model.speed : model.cost, y: model.success, z: 220 + model.coverage * 2.2, label: model.label, name: model.label, color: model.color, id: model.id, attempts: model.attempts, coverage: model.coverage })), [metric]);
  return <div className="signal-scatter-chart"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 14, right: 17, bottom: 6, left: -6 }}>
    <CartesianGrid stroke="#27313a" strokeDasharray="3 5" vertical={false} />
    <XAxis type="number" dataKey="x" name={xMetric} domain={metric === "speed" ? [0, 85] : [0, 4.2]} tick={{ fontSize: 10, fill: "#8d9aa3" }} axisLine={{ stroke: "#38434c" }} tickLine={false} tickFormatter={(v: number) => metric === "speed" ? `${v}s` : `$${v}`} label={{ value: xMetric, position: "insideBottom", offset: -3, fill: "#7d8992", fontSize: 9 }} />
    <YAxis type="number" dataKey="y" name="Ground Truth success" domain={[45, 100]} tick={{ fontSize: 10, fill: "#8d9aa3" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}%`} width={43} />
    <ZAxis type="number" dataKey="z" range={[80, 190]} name="Evidence coverage" />
    <Tooltip cursor={{ strokeDasharray: "3 4", stroke: "#839099" }} formatter={formatScatterTooltip} labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? "Preview model"} contentStyle={{ background: "#182128", border: "1px solid #364149", borderRadius: 7, color: "#eff5f2", fontSize: 11 }} />
    <Scatter data={plotted} onClick={(point: ScatterPointItem) => {
      const modelId = (point.payload as { id?: string } | undefined)?.id;
      if (modelId) onModelSelect(modelId);
    }} cursor="pointer">{plotted.map((point) => <Cell key={point.id} fill={point.color} opacity={point.id === selectedModelId ? 1 : .77} stroke={point.id === selectedModelId ? "#f5f8f2" : "#202b31"} strokeWidth={point.id === selectedModelId ? 2 : 1} />)}</Scatter>
  </ScatterChart></ResponsiveContainer><div className="signal-chart-legend"><span>● success</span><span>Bubble area = cases evaluated</span><span>Every point is illustrative</span></div></div>;
}

function ModelRows({ props, filter, setFilter }: { props: DirectionProps; filter: string; setFilter: (value: string) => void }) {
  const sorted = [...models].sort((a, b) => props.metric === "success" ? b.success - a.success : props.metric === "cost" ? a.cost - b.cost : a.speed - b.speed).filter((model) => `${model.label} ${model.family}`.toLowerCase().includes(filter.toLowerCase()));
  return <Panel className="signal-rank-panel" eyebrow="COMPARABLE DEMO COHORT · 8 CASES" title="Model leaderboard" action={<SearchBox value={filter} onChange={setFilter} placeholder="Filter models" />}>
    <div className="signal-rank-column-label"><span>MODEL</span><span>{metricName[props.metric].toUpperCase()}</span><span>CASES</span></div>
    <div className="signal-rank-list">{sorted.map((model, index) => <button className={`signal-rank-row ${props.selectedModelId === model.id ? "signal-rank-row-selected" : ""}`} key={model.id} onClick={() => props.onModelSelect(model.id)} aria-pressed={props.selectedModelId === model.id}><span className="signal-rank-num">{String(index + 1).padStart(2, "0")}</span><span className="signal-rank-model"><span className="signal-model-dot" style={{ background: model.color }} /><span><strong>{model.label}</strong><small>{model.family}</small></span></span><strong className="signal-rank-value">{formatMetric(model, props.metric)}</strong><span className="signal-rank-coverage">{model.coverage}%<small>{model.attempts} tries</small></span></button>)}</div>
    <div className="signal-rank-foot"><ShieldAlert size={13} /><span>One shared case set · missing scores stay unknown</span></div>
  </Panel>;
}

function SelectedModel({ model, metric }: { model: ModelScore; metric: MetricId }) {
  return <Panel className="signal-model-detail" eyebrow="SELECTED MODEL · SAMPLE RECORDS" title={<span className="signal-selected-heading"><i style={{ background: model.color }} />{model.label}</span>} action={<button className="signal-link-button">Open eval runs <ArrowUpRight size={13} /></button>}>
    <div className="signal-model-metrics"><MetricSummary model={model} metric={metric} /><span className="signal-detail-divider" /><div><span>ATTEMPTS WITH OUTCOME</span><b>{model.attempts} <small>/ 40</small></b><small>{model.coverage}% shared case coverage</small></div><span className="signal-detail-divider" /><div><span>MEAN PER ATTEMPT</span><b>{formatDollars(model.cost)} <small>· {model.speed}s</small></b><small>reported cost and runtime · sample</small></div></div>
    <div className="signal-config-line"><span><Database size={12} /> API / Knowledge</span><b>fixed · sample cohort</b><span>DebugAgent</span><b>{model.label}</b><span>Technique</span><b>stepByStep</b><span>Run provenance</span><b>eval-042 · demo:8c12fe2</b></div>
  </Panel>;
}

function ExplorerPage({ props }: { props: DirectionProps }) {
  const [filter, setFilter] = useState("");
  const model = models.find((row) => row.id === props.selectedModelId) ?? models[0];
  return <div className="signal-page signal-explorer-page">
    <PageHeading eyebrow="EVALUATION INTELLIGENCE / 05 MODELS" title="Find the model that fits the work." detail="Compare Ground Truth success, cost, and speed across the same sample cases. Open a point to follow its evidence back to the eval run." action={<button className="signal-scope-control">All recorded runs <ChevronDown size={13} /></button>} />
    <div className="signal-kpi-row"><Kpi icon={<Layers3 size={15} />} label="MODELS IN SAMPLE" value="05" foot="2 open · 3 hosted" /><Kpi icon={<ShieldCheck size={15} />} label="EVAL CASES SHARED" value="08" foot="Coverage shown per model" /><Kpi icon={<Database size={15} />} label="KNOWN ATTEMPTS" value="185" foot="Unknown outcomes excluded" /><Kpi icon={<Workflow size={15} />} label="COMPARE CONDITIONS" value="4" foot="Model · case · technique · run" /></div>
    <div className="signal-leaderboard-head"><MetricTabs metric={props.metric} onChange={props.onMetricChange} /><span className="signal-cohort-tag"><i /> SHARED CASE COHORT · SAMPLE</span></div>
    <div className="signal-explorer-grid"><ModelRows props={props} filter={filter} setFilter={setFilter} /><Panel className="signal-chart-panel" eyebrow="MODEL EFFICIENCY FRONTIER" title={`Ground Truth success vs ${props.metric === "speed" ? "runtime" : "cost"}`} action={<button className="signal-sort-action"><ArrowDownWideNarrow size={13} /> 40 attempts</button>}><div className="signal-plot-legend"><span><i className="signal-y-dot" /> Ground Truth repair success</span><span><i className="signal-x-dot" /> Click a point to inspect a model</span></div><ScoreScatter metric={props.metric} selectedModelId={model.id} onModelSelect={props.onModelSelect} /><div className="signal-chart-caption"><b>LEADER</b><span>{model.label}</span><strong>{formatMetric(model, props.metric)}</strong><span>· {model.coverage}% of shared cases</span></div></Panel></div>
    <SelectedModel model={model} metric={props.metric} />
    <Panel className="signal-heatmap-panel" eyebrow="CASE LEVEL · SHARED TESTS" title="Where the score comes from" action={<span className="signal-heatmap-scale"><i /> lower <i /> higher pass rate · — unknown</span>}><CaseMatrix selectedCaseId={props.selectedCaseId} onSelect={props.onCaseSelect} compact /><div className="signal-provenance-note"><span><i /> {cases.find((row) => row.id === props.selectedCaseId)?.label ?? cases[0].label}</span><small>Click a case row to trace its attempts. Both Ground Truth and Verification remain visible in run details.</small><button className="signal-link-button">View source run <ArrowUpRight size={12} /></button></div></Panel>
    <div className="signal-source-footer"><Database size={12} /> Illustrative preview only · incomplete provenance and measurements would be marked explicitly · no live eval data shown</div>
  </div>;
}

function Kpi({ icon, label, value, foot }: { icon: React.ReactNode; label: string; value: string; foot: string }) {
  return <article className="signal-kpi"><span>{icon}{label}</span><b>{value}</b><small>{foot}</small></article>;
}

function ExecutionPage({ props }: { props: DirectionProps }) {
  const [query, setQuery] = useState("");
  const [selectedEvent, setSelectedEvent] = useState(8);
  const filteredEvents = events.filter((event) => `${event.stage} ${event.message} ${event.detail} ${event.level}`.toLowerCase().includes(query.toLowerCase()));
  const current = events[selectedEvent] ?? events[0];
  return <div className="signal-page signal-execution-page">
    <PageHeading eyebrow="WORKSPACE / EXECUTION TRACE" title="Every step, visible." detail="Follow the check, model attempt, verification, and restore as they happen. This execution is sample playback; it does not touch the lab." action={<Pill tone="live" dot>DEMO ACTIVE</Pill>} />
    <Panel className="signal-active-job" eyebrow="CAMPAIGN · SERIAL LANE" title="Run 042 · benchmark comparison" action={<button className={`signal-follow-toggle ${props.live ? "is-following" : ""}`} onClick={() => props.onLiveChange(!props.live)}><Radio size={13} />{props.live ? "Follow live" : "Paused"}</button>}><JobSummary onView={() => setSelectedEvent(8)} /></Panel>
    <Panel className="signal-stage-panel" eyebrow="RUN LIFECYCLE" title="Attempt 17 of 40 · wrong_port" action={<span className="signal-elapsed"><Activity size={13} /> 04:21 elapsed · sample</span>}><StepTimeline active={3} /></Panel>
    <div className="signal-run-grid">
      <Panel className="signal-step-list" eyebrow="EVENT TIMELINE" title="Inspect what happened" action={<span className="signal-event-count">10 events</span>}>
        <SearchBox value={query} onChange={setQuery} placeholder="Filter stages, events, levels" />
        <div className="signal-events-list">{filteredEvents.map((event) => { const idx = events.indexOf(event); return <button key={`${event.time}-${event.stage}`} onClick={() => setSelectedEvent(idx)} className={`signal-event ${selectedEvent === idx ? "signal-event-selected" : ""} signal-event-${event.level.toLowerCase()}`} aria-pressed={selectedEvent === idx}><time>{event.time}</time><i className="signal-event-glyph">{event.level === "OK" ? "✓" : event.level === "ERROR" ? "!" : event.level === "WARN" ? "△" : "·"}</i><span><b>{event.message}</b><small>{event.stage} · {event.level}</small></span></button>; })}</div>
        <div className="signal-event-inspector"><span className="signal-inspector-label">SELECTED EVENT · {current.level}</span><b>{current.message}</b><p>{current.detail}</p><span><Timer size={11} /> {current.time} <i>·</i> {current.stage}</span></div>
      </Panel>
      <div className="signal-output-column"><Panel className="signal-console-panel" eyebrow="LIVE COMMAND OUTPUT" title={<span className="signal-title-terminal"><Terminal size={15} /> worker.log</span>} action={<div className="signal-terminal-controls"><Pill tone="live" dot>STREAMING · SAMPLE</Pill><button onClick={() => props.onLiveChange(!props.live)}>{props.live ? "Pause" : "Resume"}</button></div>}>
        <div className="signal-console-body" aria-label="Illustrative execution output">
          {events.map((event, index) => <button key={`${event.time}-${index}`} className={`signal-log-line signal-log-${event.level.toLowerCase()} ${index === selectedEvent ? "signal-log-selected" : ""}`} onClick={() => setSelectedEvent(index)}><span>{event.time}</span><b>{event.level === "OK" ? "✓" : event.level === "WARN" ? "!" : event.level === "ERROR" ? "×" : "›"}</b><span><i>{event.stage}</i> {event.message}<small>{event.detail}</small></span></button>)}
        </div><div className="signal-console-footer"><span><i /> Full event buffer · safe preview output</span><span>Auto-follow {props.live ? "on" : "off"}</span></div>
      </Panel></div>
      <div className="signal-evidence-rail"><Panel className="signal-check-summary" eyebrow="CHECKS PASSED · 4 OF 5" title="Readiness signals"><div className="signal-checks">{["Repository identity", "PostgreSQL / pgvector", "Kubernetes access", "RAG service", "Baseline restoration"].map((name, i) => <div key={name} className={i === 4 ? "signal-check-fail" : "signal-check-pass"}>{i === 4 ? <TriangleAlert size={14} /> : <ShieldCheck size={14} />}<span><b>{name}</b><small>{i === 4 ? "Failure after case · restore needed" : "Passed · selected lane"}</small></span><i>{i === 4 ? "ACTION" : "PASS"}</i></div>)}</div><button className="signal-repair-hint" onClick={() => setSelectedEvent(8)}><ShieldAlert size={12} /> Fixture restored in this sample · inspect cleanup step <ArrowUpRight size={11} /></button></Panel><div className="signal-ownership-note"><ShieldCheck size={15} /><span><b>Lane scoped</b><small>Only selected lane resources may be changed by the runner.</small></span></div></div>
    </div>
    <div className="signal-execution-trace"><TraceTable dense /></div>
  </div>;
}

function ProfileList({ selected, onSelect }: { selected: string; onSelect: (id: string) => void }) {
  return <Panel className="signal-profile-list" eyebrow="LOCAL INVENTORY · READ ONLY" title="Lab profiles" action={<button aria-label="Refresh profile inventory" className="signal-refresh"><Activity size={13} /> refresh</button>}><div className="signal-profile-rows">{profiles.map((profile) => <button key={profile.id} onClick={() => onSelect(profile.id)} className={selected === profile.id ? "selected" : ""} aria-pressed={selected === profile.id}><i className={`signal-profile-status signal-status-${profile.status}`} /><span><b>{profile.label}</b><small>{profile.context}</small></span><em>{profile.status === "running" ? `${profile.pods} pods` : profile.status}</em></button>)}</div><p className="signal-readonly-note"><ShieldCheck size={12} /> Other local profiles remain read only</p></Panel>;
}

function LabPage() {
  const [selectedProfile, setSelectedProfile] = useState(profiles.find((profile) => profile.affected)?.id ?? profiles[0].id);
  const selected = profiles.find((profile) => profile.id === selectedProfile) ?? profiles[0];
  return <div className="signal-page signal-lab-page">
    <PageHeading eyebrow="INFRASTRUCTURE / OBSERVED STATE" title="See what the run can touch." detail="Inspect the lab host, local profile inventory, and job-linked resources together. Each reading here is illustrative preview data." action={<button className="signal-scope-control"><Server size={13} /> Lab host · sample</button>} />
    <div className="signal-lab-status-row"><Pill tone="live" dot>2 GPUs · sample</Pill><span>Read only · local inventory</span><span>Updated just now · simulated</span><button onClick={() => setSelectedProfile(profiles[0].id)}><Activity size={13} /> Reset selected lane</button></div>
    <Panel className="signal-topology-panel" eyebrow="LAB RESOURCE MAP" title="Host → profile → workload" action={<div className="signal-topology-legend"><span><i /> Selected lane</span><span><i /> Host observation</span><span><i /> Other profile</span></div>}><LabTopology dense /><div className="signal-selected-profile-note"><span><i className={`signal-profile-status signal-status-${selected.status}`} /> <b>{selected.label}</b> · {selected.status}</span><span>{selected.nodes} nodes · {selected.workloads} workloads · {selected.pods} pods</span><Pill tone={selected.affected ? "live" : "muted"}>{selected.affected ? "CAMPAIGN LINKED · DEMO" : "READ ONLY"}</Pill></div></Panel>
    <div className="signal-lab-grid"><ProfileList selected={selectedProfile} onSelect={setSelectedProfile} /><Panel className="signal-host-trend" eyebrow="RESOURCE WINDOW · LAST 2H" title="Run time and shared load" action={<div className="signal-load-label"><CircleDot size={12} /> {selected.affected ? "Run in progress · sample" : "No active lane selected"}</div>}><div className="signal-trend-legend"><span><i className="signal-cpu-key" /> CPU</span><span><i className="signal-gpu-key" /> GPU 0</span><span><i className="signal-gpu-second-key" /> GPU 1</span><span className="signal-overlap-label">Shading shows illustrative eval window</span></div><HostTrendChart /><div className="signal-load-caption">Measured activity and confirmed workload ownership appear separately in the live app.</div></Panel></div>
    <div className="signal-gpu-cards"><Panel eyebrow="ACCELERATOR TELEMETRY · SAMPLE" title="A40 utilization and memory"><div className="signal-gpu-trends"><article><div><span>GPU 0 · NVIDIA A40</span><b>{resources.at(-1)?.gpu0}% <small>GPU</small></b></div><ProgressMeter value={resources.at(-1)?.gpu0 ?? 0} tone="teal" showValue={false} /><small>{resources.at(-1)?.vram0.toFixed(1)} / 46 GB VRAM · illustrative</small><ResourceChart metric="gpu" compact /></article><article><div><span>GPU 1 · NVIDIA A40</span><b>{resources.at(-1)?.gpu1}% <small>GPU</small></b></div><ProgressMeter value={resources.at(-1)?.gpu1 ?? 0} tone="violet" showValue={false} /><small>{resources.at(-1)?.vram1.toFixed(1)} / 46 GB VRAM · illustrative</small><ResourceChart metric="gpu" compact /></article></div></Panel><ResourceTiles compact /></div>
    <Panel className="signal-workload-summary" eyebrow="AFFECTED WORKLOAD · EVAL-DEMO-042" title="Who is using the accelerator?" action={<Pill tone="warn" dot>Attribution is a sample</Pill>}><div className="signal-workload-row"><div><span><Layers3 size={14} /> debug-agent inference</span><b>GPU 0 · allocated to selected demo run</b></div><ProgressMeter value={78} tone="teal" /><span className="signal-resource-relationship">profile relationship: <strong>confirmed in preview</strong><br /><small>Attribution needs pod/resource mapping in the live data source.</small></span></div></Panel>
    <div className="signal-source-footer"><HardDrive size={12} /> Activity unrelated to a confirmed run stays labeled “host observed” · other profiles are read only</div>
  </div>;
}

export function Signal(props: DirectionProps) {
  return <div className="signal-shell">
    <header className="signal-topbar"><a className="signal-brand" href="#" onClick={(event) => { event.preventDefault(); props.onPageChange("explorer"); }}><span>⌁</span><b>KubeLLM</b><small>OPERATOR / SIGNAL</small></a><span className="signal-context"><Server size={13} /> lab host <b>·</b> research lane <ChevronDown size={12} /></span><HostStrip /><div className="signal-user-chip"><span>●</span> PREVIEW · LOCAL</div></header>
    <DemoBanner />
    <div className="signal-workspace"><Navigation page={props.page} onPageChange={props.onPageChange} /><main className="signal-content">{props.page === "explorer" ? <ExplorerPage props={props} /> : props.page === "execution" ? <ExecutionPage props={props} /> : <LabPage />}</main></div>
  </div>;
}
