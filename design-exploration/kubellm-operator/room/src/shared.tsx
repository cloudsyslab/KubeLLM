import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Handle, MiniMap, Position, ReactFlow } from "@xyflow/react";
import type { Edge, Node, NodeProps } from "@xyflow/react";
import { Activity, ArrowDownRight, ArrowUpRight, Check, ChevronRight, CircleAlert, Cpu, Database, Gauge, GitBranch, HardDrive, Layers, MemoryStick, Network, Pause, Play, Radio, RefreshCw, Search, ShieldCheck, Terminal, TriangleAlert } from "lucide-react";
import type { EvalCase, LabProfile, MetricId, ModelScore, ResourcePoint, Tone } from "./domain";
import { cases, evalHistory, events, formatDollars, formatRate, illustrativeNotice, metricLabel, models, profiles, resources } from "./data";

export { Activity, ArrowDownRight, ArrowUpRight, Check, ChevronRight, CircleAlert, Cpu, Database, Gauge, GitBranch, HardDrive, Layers, MemoryStick, Network, Pause, Play, Radio, RefreshCw, Search, ShieldCheck, Terminal, TriangleAlert };
export { cases, evalHistory, events, formatDollars, formatRate, illustrativeNotice, metricLabel, models, profiles, resources };
export type { EvalCase, LabProfile, MetricId, ModelScore, ResourcePoint, Tone };

export function DemoBanner({ small = false }: { small?: boolean }) {
  return (
    <div className={`demo-banner${small ? " demo-banner-small" : ""}`} role="note">
      <span className="demo-mark" />
      <span><strong>PREVIEW SIMULATION</strong><em>Illustrative sample data · no benchmark or cluster action is running</em></span>
    </div>
  );
}

export function Pill({ children, tone = "muted", dot = false, className = "" }: { children: React.ReactNode; tone?: Tone; dot?: boolean; className?: string }) {
  return <span className={`pill pill-${tone} ${className}`}>{dot && <i className="status-pip" />}{children}</span>;
}

export function Eyebrow({ children, icon, className = "" }: { children: React.ReactNode; icon?: React.ReactNode; className?: string }) {
  return <div className={`eyebrow ${className}`}>{icon}{children}</div>;
}

export function Panel({ children, className = "", title, eyebrow, icon, action }: { children: React.ReactNode; className?: string; title?: React.ReactNode; eyebrow?: string; icon?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className={`panel ${className}`}>
      {(title || eyebrow) && <header className="panel-header"><div>{eyebrow && <Eyebrow icon={icon}>{eyebrow}</Eyebrow>}{title && <h3>{title}</h3>}</div>{action}</header>}
      {children}
    </section>
  );
}

export function PageHeading({ eyebrow, title, detail, action }: { eyebrow: string; title: React.ReactNode; detail?: React.ReactNode; action?: React.ReactNode }) {
  return <div className="page-heading"><div><Eyebrow>{eyebrow}</Eyebrow><h1>{title}</h1>{detail && <p>{detail}</p>}</div>{action}</div>;
}

export function ProgressMeter({ value, label, tone = "teal", showValue = true }: { value: number; label?: string; tone?: string; showValue?: boolean }) {
  return <div className="meter-wrap" aria-label={`${value}%${label ? ` ${label}` : ""}`}><div className="meter-track"><span className={`meter-fill tone-${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>{showValue && <span className="meter-value">{value}%</span>}</div>;
}

export function Delta({ value, suffix = "pts" }: { value: number; suffix?: string }) {
  const positive = value > 0;
  return <span className={`delta ${positive ? "delta-positive" : "delta-negative"}`}>{positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{Math.abs(value).toFixed(1)} {suffix}</span>;
}

function ValueTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value?: number; name?: string; color?: string; dataKey?: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map((item) => <span key={item.dataKey ?? item.name} style={{ color: item.color }}>{item.name}: {typeof item.value === "number" ? item.value.toFixed(1) : item.value}</span>)}</div>;
}

export function SuccessChart({ compact = false }: { compact?: boolean }) {
  const chart = useMemo(() => models.map((m) => ({ name: m.label.split(" ")[0], model: m.label, score: m.success, cost: m.cost, fill: m.color })), []);
  return (
    <div className={`success-chart${compact ? " success-chart-compact" : ""}`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chart} margin={{ top: 10, right: 10, left: -12, bottom: 0 }}>
          <defs><linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#14745f" stopOpacity={0.22} /><stop offset="96%" stopColor="#14745f" stopOpacity={0.01} /></linearGradient></defs>
          <CartesianGrid stroke="#e9ece6" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#778178", fontSize: 11 }} dy={7} />
          <YAxis domain={[45, 100]} tickFormatter={(value) => `${value}%`} axisLine={false} tickLine={false} tick={{ fill: "#89918b", fontSize: 10 }} />
          <Tooltip content={<ValueTooltip />} labelFormatter={(_, payload) => payload?.[0]?.payload?.model ?? ""} />
          <Area type="monotone" dataKey="score" name="Ground Truth" stroke="#14745f" strokeWidth={2.6} fill="url(#scoreFill)" activeDot={{ r: 5, fill: "#fff", stroke: "#14745f", strokeWidth: 2.5 }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ResourceChart({ metric = "gpu", compact = false }: { metric?: "gpu" | "host"; compact?: boolean }) {
  const type = metric === "host" ? "host" : "gpu";
  return (
    <div className={`resource-chart ${compact ? "resource-chart-compact" : ""}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={resources} margin={{ top: 10, right: 8, left: -17, bottom: 0 }}>
          <CartesianGrid stroke="#e8ebe6" vertical={false} strokeDasharray="3 5" />
          <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: "#7e8881", fontSize: 10 }} interval={5} />
          <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}`} axisLine={false} tickLine={false} tick={{ fill: "#89918b", fontSize: 10 }} />
          <Tooltip content={<ValueTooltip />} />
          {type === "host" ? <><Line type="monotone" dataKey="cpu" name="CPU %" stroke="#6682d4" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="memory" name="Memory %" stroke="#bb7e44" strokeWidth={2} dot={false} /></> : <><Line type="monotone" dataKey="gpu0" name="GPU 0 %" stroke="#13826c" strokeWidth={2.3} dot={false} /><Line type="monotone" dataKey="gpu1" name="GPU 1 %" stroke="#7e66d5" strokeWidth={2.3} dot={false} /></>}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Sparkline({ data, color = "currentColor", height = 26 }: { data: number[]; color?: string; height?: number }) {
  const points = data.map((value, index) => `${(index / Math.max(1, data.length - 1)) * 100},${height - 2 - (value / 100) * (height - 5)}`).join(" ");
  const end = data.at(-1) ?? 0;
  return <svg aria-hidden="true" className="sparkline" viewBox={`0 0 100 ${height}`} preserveAspectRatio="none"><polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" /><circle cx="100" cy={height - 2 - (end / 100) * (height - 5)} r="2.1" fill={color} vectorEffect="non-scaling-stroke" /></svg>;
}

export function CaseMatrix({ selectedCaseId, onSelect, compact = false }: { selectedCaseId: string; onSelect: (id: string) => void; compact?: boolean }) {
  return (
    <div className={`case-matrix-scroll${compact ? " case-matrix-compact" : ""}`}>
      <table className="case-matrix"><thead><tr><th>Eval case</th>{models.map((model) => <th key={model.id} title={model.label}>{model.label.split(" ").slice(0, 2).join(" ")}</th>)}</tr></thead><tbody>{cases.map((test, index) => <tr key={test.id} className={selectedCaseId === test.id ? "case-row-selected" : ""} onClick={() => onSelect(test.id)}><td><span>{test.label}</span><small>{test.area}</small></td>{test.scores.map((score, modelIndex) => <td key={`${test.id}-${models[modelIndex].id}`}><span className={`matrix-cell ${score == null ? "matrix-unknown" : score >= 80 ? "matrix-high" : score >= 60 ? "matrix-mid" : "matrix-low"}`} title={score == null ? `${models[modelIndex].label}: unknown Ground Truth` : `${models[modelIndex].label}: ${score}% Ground Truth`} tabIndex={0} onKeyDown={(event) => event.key === "Enter" && onSelect(test.id)}>{score == null ? "—" : `${score}%`}</span></td>)}</tr>)}</tbody></table>
    </div>
  );
}

export function MiniTerminal({ onErrorSelect, tight = false }: { onErrorSelect?: () => void; tight?: boolean }) {
  const [autoFollow, setAutoFollow] = useState(true);
  return (
    <div className={`terminal-window${tight ? " terminal-tight" : ""}`}>
      <div className="terminal-toolbar"><div><span className="terminal-led" /><span className="terminal-led" /><span className="terminal-led" /><span className="terminal-path">readiness.log</span></div><div><span className="terminal-state">DEMO STREAM</span><button className="terminal-follow" onClick={() => setAutoFollow((state) => !state)} aria-pressed={autoFollow}>{autoFollow ? "FOLLOWING" : "PAUSED"}</button></div></div>
      <div className="terminal-body" aria-label="Illustrative sample command output">
        {events.map((event, index) => <button key={`${event.time}-${index}`} className={`terminal-row terminal-${event.level.toLowerCase()}`} onClick={() => event.level === "ERROR" && onErrorSelect?.()}><time>{event.time}</time><b>{event.level === "OK" ? "✓" : event.level === "WARN" ? "!" : event.level === "ERROR" ? "×" : "·"}</b><span><small>{event.stage}</small>{event.message}<em>{event.detail}</em></span></button>)}
      </div>
      <div className="terminal-foot"><span>Last line 00:04.021 · buffer preserved across refresh</span><button onClick={() => setAutoFollow(true)}>Jump to latest <ChevronRight size={13} /></button></div>
    </div>
  );
}

interface ProfileNode extends Record<string, unknown> { profile: LabProfile; selected: boolean; }
function ProfileCardNode({ data }: NodeProps<Node<ProfileNode>>) {
  const { profile } = data;
  return <div className={`topology-node topology-profile topology-${profile.status}${profile.affected ? " topology-affected" : ""}`}>
    <div className="topology-node-top"><span className={`status-pip pip-${profile.status}`} />PROFILE · {profile.status.toUpperCase()}</div>
    <strong>{profile.label}</strong>
    <span>{profile.nodes} nodes <i>·</i> {profile.workloads} workloads <i>·</i> {profile.pods} pods</span>
    <small>{profile.affected ? "ACTIVE DEMO · owned lane" : profile.context}</small>
    <Handle type="target" position={Position.Left} />
    <Handle type="source" position={Position.Right} />
  </div>;
}

function ResourceNode({ data }: NodeProps<Node<{ title: string; subtitle: string; stat: string; icon: string; kind?: string }>>) {
  const Icon = data.icon === "gpu" ? Gauge : data.icon === "pod" ? Layers : data.icon === "cpu" ? Cpu : Network;
  return <div className={`topology-node topology-resource${data.kind ? ` topology-resource-${data.kind}` : ""}`}><Handle type="target" position={Position.Left} /><div className="resource-node-icon"><Icon size={15} /></div><span><strong>{data.title}</strong><small>{data.subtitle}</small></span><b>{data.stat}</b></div>;
}

const nodeTypes = { profileCard: ProfileCardNode, resourceCard: ResourceNode };
const profilePositions: Array<[number, number]> = [[40, 12], [40, 152], [40, 292], [40, 432]];

export function LabTopology({ dense = false }: { dense?: boolean }) {
  const [selected, setSelected] = useState("research-lane");
  const nodeList = useMemo<Node[]>(() => [
    { id: "host", type: "resourceCard", position: { x: 5, y: 223 }, data: { title: "lab host", subtitle: "2 × NVIDIA A40", stat: "online", icon: "cpu", kind: "host" }, draggable: false },
    ...profiles.map((profile, index) => ({ id: profile.id, type: "profileCard", position: { x: 330, y: profilePositions[index][1] }, data: { profile, selected: profile.id === selected }, draggable: false })),
    { id: "workload", type: "resourceCard", position: { x: 748, y: 206 }, data: { title: "eval workload", subtitle: "lane-owned · sample", stat: "running", icon: "pod", kind: "workload" }, draggable: false },
    { id: "gpu", type: "resourceCard", position: { x: 748, y: 332 }, data: { title: "GPU allocation", subtitle: "shared utilization", stat: "82% · demo", icon: "gpu", kind: "gpu" }, draggable: false },
  ], [selected]);
  const edgeList = useMemo<Edge[]>(() => [
    ...profiles.map((profile) => ({ id: `host-${profile.id}`, source: "host", target: profile.id, animated: profile.affected, type: "smoothstep", style: { stroke: profile.affected ? "#13846e" : "#c7ceca", strokeWidth: profile.affected ? 2.5 : 1.2 } })),
    { id: "lane-workload", source: "research-lane", target: "workload", animated: true, type: "smoothstep", style: { stroke: "#13846e", strokeWidth: 2.5 } },
    { id: "host-gpu", source: "host", target: "gpu", animated: true, type: "smoothstep", style: { stroke: "#8065da", strokeWidth: 2.5, strokeDasharray: "5 3" } },
  ], []);
  return <div className={`lab-topology${dense ? " lab-topology-dense" : ""}`}><div className="topology-key"><span><i className="topology-key-active" />job-linked</span><span><i className="topology-key-host" />host observed</span><span><i className="topology-key-readonly" />other local profile · read only</span></div><div className="reactflow-stage"><ReactFlow<Node, Edge> nodes={nodeList} edges={edgeList} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.12 }} minZoom={0.36} maxZoom={1.6} nodesConnectable={false} elementsSelectable panOnDrag zoomOnScroll proOptions={{ hideAttribution: true }} onNodeClick={(_, node) => { if (profiles.some((profile) => profile.id === node.id)) setSelected(node.id); }}><MiniMap pannable zoomable nodeColor={(node) => node.id === "research-lane" ? "#1b9278" : node.id === "host" ? "#5368ad" : "#a9b5ad"} /><div className="reactflow-overlay">Select a profile to inspect <span> · </span>actions confined to selected lane</div></ReactFlow></div></div>;
}

export function ResourceTiles({ compact = false }: { compact?: boolean }) {
  const latest = resources.at(-1)!;
  const [processIndex, setProcessIndex] = useState(0);
  const processRows = [
    { pid: "34120", task: "llm-worker", cpu: "242%", memory: "18.4 GB", gpu: "GPU 0 · 81%" },
    { pid: "33794", task: "rag-api", cpu: "5.8%", memory: "1.2 GB", gpu: "—" },
    { pid: "33918", task: "eval-runner", cpu: "8.3%", memory: "2.6 GB", gpu: "—" },
    { pid: "31102", task: "kubelet", cpu: "2.1%", memory: "0.8 GB", gpu: "—" },
  ];
  return <div className={`resource-tiles${compact ? " resource-tiles-compact" : ""}`}>
    <div className="host-metrics-row"><ResourceTile icon={<Cpu size={15} />} label="CPU" value="68%" detail="32 vCPU · demo" percent={68} color="blue" /><ResourceTile icon={<MemoryStick size={15} />} label="MEMORY" value="58%" detail="91 / 157 GB · demo" percent={58} color="amber" /><ResourceTile icon={<HardDrive size={15} />} label="STORAGE" value="41%" detail="256 / 620 GB · demo" percent={41} color="plum" /></div>
    <div className="gpu-metrics-row">
      {[0, 1].map((gpu) => { const load = gpu === 0 ? latest.gpu0 : latest.gpu1; const memory = gpu === 0 ? latest.vram0 : latest.vram1; return <article className={`gpu-card gpu-card-${gpu}`} key={gpu}><div className="gpu-card-head"><span><Gauge size={15} /><b>GPU {gpu}</b></span><Pill tone="live" dot>DEMO</Pill></div><div className="gpu-model">NVIDIA A40 <span>· 46 GB</span></div><div className="gpu-readouts"><strong>{load}%<small>UTILIZATION</small></strong><strong>{memory.toFixed(1)} <small>/ 46 GB VRAM</small></strong></div><ProgressMeter value={load} tone={gpu === 0 ? "teal" : "violet"} showValue={false} /></article>; })}
    </div>
    <Panel className="process-panel" title="Top processes" eyebrow="HOST ACTIVITY" icon={<Activity size={13} />} action={<button className="text-action" onClick={() => setProcessIndex((index) => (index + 1) % 2)}><RefreshCw size={12} /> {processIndex ? "Refresh paused" : "Sample 1s"}</button>}>
      <div className="process-table-wrap"><table className="process-table"><thead><tr><th>PROCESS</th><th>CPU</th><th>MEMORY</th><th>ACCELERATOR</th></tr></thead><tbody>{processRows.slice(processIndex ? 1 : 0, processIndex ? 4 : 4).map((process) => <tr key={process.pid}><td><code>{process.task}</code><small>PID {process.pid} · sample</small></td><td>{process.cpu}</td><td>{process.memory}</td><td>{process.gpu}</td></tr>)}</tbody></table></div>
      <p className="safe-note"><ShieldCheck size={12} />Illustrative process snapshot; environment variables and command arguments stay hidden.</p>
    </Panel>
  </div>;
}

function ResourceTile({ icon, label, value, detail, percent, color }: { icon: React.ReactNode; label: string; value: string; detail: string; percent: number; color: string }) {
  return <article className="resource-tile"><div className={`resource-tile-icon resource-${color}`}>{icon}</div><div className="resource-tile-body"><span>{label}</span><b>{value}</b><small>{detail}</small><ProgressMeter value={percent} tone={color} showValue={false} /></div></article>;
}

export function StepTimeline({ active = 3, compact = false }: { active?: number; compact?: boolean }) {
  const stages = ["Preflight", "Start lane", "Run evals", "Verify", "Teardown"];
  return <ol className={`step-timeline${compact ? " step-timeline-compact" : ""}`}>{stages.map((stage, index) => { const complete = index < active - 1; const running = index === active - 1; return <li key={stage} className={complete ? "step-complete" : running ? "step-running" : "step-pending"}><span className="step-marker">{complete ? <Check size={12} /> : running ? <i className="step-spin" /> : index + 1}</span><span>{stage}</span>{index < stages.length - 1 && <span className="step-link" />}</li>; })}</ol>;
}

export function JobSummary({ onView }: { onView?: () => void }) {
  return <div className="job-summary"><div className="job-summary-top"><div><Pill tone="live" dot>RUNNING · DEMO</Pill><span className="job-code">EVAL-DEMO-042</span></div><strong>140 <i>/</i> 200 <small>requests</small></strong></div><ProgressMeter value={70} label="requests processed"/><div className="job-meta-row"><span>Model comparison</span><b>Cedar 32B vs Northstar Large</b><span>Started 04:21 ago · illustrative</span>{onView && <button className="text-action" onClick={onView}>View live run <ChevronRight size={13} /></button>}</div></div>;
}

export function SearchBox({ value, onChange, placeholder = "Filter cases and runs" }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="search-box"><Search size={14} /><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={placeholder} /></label>;
}

export function LegendDot({ color, children }: { color: string; children: React.ReactNode }) {
  return <span className="chart-legend-dot"><i style={{ background: color }} />{children}</span>;
}

export function LabelCell({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={`label-cell label-cell-${tone}`}><i className="status-pip" />{children}</span>;
}

export function TraceTable({ dense = false }: { dense?: boolean }) {
  const [search, setSearch] = useState("");
  const rows = cases.filter((test) => `${test.id} ${test.label} ${test.area}`.toLowerCase().includes(search.toLowerCase()));
  return <Panel className={`trace-panel${dense ? " trace-panel-dense" : ""}`} eyebrow="EVAL EVIDENCE" title="Latest case outcomes" icon={<Database size={13} />} action={<SearchBox value={search} onChange={setSearch} placeholder="Filter cases" />}>
    <div className="trace-table-wrap"><table className="trace-table"><thead><tr><th>CASE</th><th>DEBUG MODEL</th><th>GROUND TRUTH</th><th>VERIFICATION</th><th>TIME</th><th>RUN</th></tr></thead><tbody>{rows.slice(0, dense ? 5 : 8).map((row, index) => <tr key={row.id} tabIndex={0}><td><b>{row.label}</b><small>{row.area} · {row.id}</small></td><td>{models[(index + 1) % models.length].label}</td><td>{row.scores[(index + 1) % 5] == null ? <LabelCell tone="muted">UNKNOWN</LabelCell> : row.scores[(index + 1) % 5]! >= 80 ? <LabelCell tone="good">PASS</LabelCell> : <LabelCell tone="bad">FAIL</LabelCell>}</td><td><LabelCell tone={index % 4 === 2 ? "warn" : "good"}>{index % 4 === 2 ? "DISAGREES" : "MATCHES"}</LabelCell></td><td>{index % 2 ? "02:14" : "01:38"}</td><td><a href="#runs" onClick={(event) => event.preventDefault()} title="Illustrative provenance row">eval-042</a></td></tr>)}</tbody></table></div>
  </Panel>;
}

export function ModelMetricChart({ metric = "success", compact = false }: { metric?: MetricId; compact?: boolean }) {
  const pointData = models.map((model) => ({ ...model, x: metric === "speed" ? model.speed : model.cost, y: model.success, z: 10 + model.attempts / 2 }));
  return <div className={`metric-scatter${compact ? " metric-scatter-compact" : ""}`}>
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={resources} margin={{ top: 10, right: 12, left: -15, bottom: 0 }}>
        <CartesianGrid stroke="#e8ebe6" vertical={false} strokeDasharray="3 5" />
        <XAxis dataKey="time" tick={{ fill: "#869089", fontSize: 9 }} axisLine={false} tickLine={false} interval={7} /><YAxis yAxisId="left" domain={[45, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "#869089", fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis yAxisId="right" orientation="right" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "#9c79c2", fontSize: 9 }} axisLine={false} tickLine={false} />
        <Tooltip content={<ValueTooltip />} /><Line yAxisId="left" dataKey="cpu" name="Host CPU" stroke="#5576d7" strokeWidth={2.2} dot={false} /><Line yAxisId="right" dataKey="gpu0" name="GPU 0 utilization" stroke="#8267b4" strokeWidth={2.1} dot={false} /><Line yAxisId="right" dataKey="gpu1" name="GPU 1 utilization" stroke="#28967b" strokeWidth={2.1} dot={false} />
      </LineChart>
    </ResponsiveContainer>
    <span className="visually-muted">{pointData.length} illustrative model profiles · cost and speed are separate dimensions</span>
  </div>;
}

export function HostTrendChart({ compact = false }: { compact?: boolean }) {
  return <div className={`host-trend-chart${compact ? " host-trend-compact" : ""}`}><ResponsiveContainer width="100%" height="100%"><LineChart data={resources} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}><XAxis dataKey="time" hide /><YAxis hide domain={[0, 100]} /><Tooltip content={<ValueTooltip />} /><Line dataKey="cpu" name="Host CPU" stroke="#5270ca" dot={false} strokeWidth={2} /><Line dataKey="gpu0" name="GPU 0" stroke="#14745f" dot={false} strokeWidth={2} /><Line dataKey="gpu1" name="GPU 1" stroke="#966eb9" dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer></div>;
}

export function MetricSummary({ model, metric }: { model: ModelScore; metric: MetricId }) {
  const primary = metric === "success" ? formatRate(model.success) : metric === "cost" ? formatDollars(model.cost) : `${model.speed.toFixed(1)}s`;
  const subtitle = metric === "success" ? "Ground Truth success" : metric === "cost" ? "per attempt · partial coverage" : "time per attempt";
  return <div className="metric-summary"><span>{metricLabel(metric).toUpperCase()}</span><b>{primary}</b><small>{subtitle}</small></div>;
}
