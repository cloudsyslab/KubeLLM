import { useMemo, useState } from "react";
import type { FC, ReactNode } from "react";
import { Activity, ArrowUpDown, ChevronDown, ChevronRight, CircleAlert, Code2, Database, Filter, GitBranch, History, Layers3, Search, ShieldCheck, SlidersHorizontal, Terminal, ArrowUpRight } from "lucide-react";
import type { DirectionProps, MetricId } from "../domain";
import { cases, evalHistory, events, illustrativeNotice, models, Pill, profiles, ResourceChart, ResourceTiles, StepTimeline } from "../shared";
import "./Fieldnotes.css";

const metricText: Record<MetricId, string> = {
  success: "Ground Truth success",
  cost: "Cost per attempt",
  speed: "Seconds per attempt",
};

const scoreText = (score: number, metric: MetricId) =>
  metric === "success" ? `${score.toFixed(1)}%` : metric === "cost" ? `$${score.toFixed(2)}` : `${score.toFixed(1)}s`;

const format = (model: (typeof models)[number], metric: MetricId) =>
  scoreText(model[metric], metric);

const toneForRate = (rate: number) => rate >= 75 ? "pass" : rate >= 65 ? "mixed" : "attention";

function StatusMark({ kind, children }: { kind: "pass" | "mixed" | "attention" | "good" | "warn" | "muted"; children: ReactNode }) {
  return <span className={`fieldnotes-status fieldnotes-status--${kind}`}><i />{children}</span>;
}

function PageIntro({ kicker, title, copy, meta }: { kicker: string; title: string; copy: string; meta: string }) {
  return <header className="fieldnotes-intro"><div className="fieldnotes-intro-title"><span className="fieldnotes-overline">{kicker}</span><h1>{title}</h1><p>{copy}</p></div><span className="fieldnotes-intro-meta"><span className="fieldnotes-led" />{meta}</span></header>;
}

const Fieldnotes: FC<DirectionProps> = ({
  page,
  onPageChange,
  metric,
  onMetricChange,
  selectedModelId,
  onModelSelect,
  selectedCaseId,
  onCaseSelect,
  live,
  onLiveChange,
}) => {
  const [search, setSearch] = useState("");
  const [sortAscending, setSortAscending] = useState(false);
  const [providerFilter, setProviderFilter] = useState<"all" | "open" | "hosted">("all");
  const [eventsOpen, setEventsOpen] = useState(true);
  const [selectedEventIndex, setSelectedEventIndex] = useState(8);
  const [profileFilter, setProfileFilter] = useState<"all" | "running" | "stopped">("all");
  const [caseAreaFilter, setCaseAreaFilter] = useState("All cases");
  const [selectedProfileId, setSelectedProfileId] = useState("research-lane");
  const selectedModel = models.find((model) => model.id === selectedModelId) ?? models[0];
  const metricValue = (model: (typeof models)[number]) => model[metric];
  const selectedMetricTop = useMemo(() => models.reduce((best, current) => metric === "success" ? (current.success > best.success ? current : best) : current[metric] < best[metric] ? current : best, models[0]), [metric]);
  const visibleModels = useMemo(() => models
    .filter((model) => providerFilter === "all" || (providerFilter === "open" ? model.family.startsWith("Open model") : model.family.startsWith("Hosted")))
    .filter((model) => `${model.label} ${model.family}`.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => (sortAscending ? 1 : -1) * (metricValue(a) - metricValue(b))), [metric, providerFilter, search, sortAscending]);
  const selectedEvent = events[selectedEventIndex] ?? events[8];
  const selectedProfile = profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0];
  const visibleProfiles = profiles.filter((profile) => profileFilter === "all" || profile.status === profileFilter);
  const visibleCases = cases.filter((test) => {
    const matchesText = `${test.id} ${test.label} ${test.area}`.toLowerCase().includes(search.toLowerCase());
    const matchesArea = caseAreaFilter === "All cases" || test.area === caseAreaFilter;
    return matchesText && matchesArea;
  });

  return (
    <div className="fieldnotes">
      <header className="fieldnotes-header">
        <a className="fieldnotes-brand" href="#explorer" onClick={(event) => { event.preventDefault(); onPageChange("explorer"); }} aria-label="KubeLLM evaluation index">
          <span className="fieldnotes-brand-mark">K</span><span><strong>kubeLLM</strong><small>RESEARCH / INDEX</small></span>
        </a>
        <div className="fieldnotes-context"><span className="fieldnotes-online"><i />LAB CONNECTED · DEMO</span><span className="fieldnotes-context-separator" /><span className="fieldnotes-context-copy">isolated lane <ChevronDown size={13} /></span><span className="fieldnotes-pod">2 × NVIDIA A40</span></div>
        <div className="fieldnotes-profile"><span className="fieldnotes-profile-avatar">M</span><span>Minh<small>RESEARCHER</small></span><ChevronDown size={13} /></div>
      </header>

      <nav className="fieldnotes-nav" aria-label="Operator sections">
        <div className="fieldnotes-nav-links">
          <button type="button" className={page === "explorer" ? "is-active" : ""} onClick={() => onPageChange("explorer")}><Database size={15} />Evaluation index</button>
          <button type="button" className={page === "execution" ? "is-active" : ""} onClick={() => onPageChange("execution")}><History size={15} />Execution ledger<PillCount /></button>
          <button type="button" className={page === "lab" ? "is-active" : ""} onClick={() => onPageChange("lab")}><Layers3 size={15} />Lab resources</button>
        </div>
        <div className="fieldnotes-nav-note"><span className="fieldnotes-led" />PRIVATE-LANE PREVIEW</div>
      </nav>

      <main className="fieldnotes-main">
        <div className="fieldnotes-illustration"><span><i />ILLUSTRATIVE SAMPLE</span><span>{illustrativeNotice}</span></div>
        {page === "explorer" && (
          <div className="fieldnotes-workspace">
            <aside className="fieldnotes-rail">
              <div className="fieldnotes-rail-top"><span className="fieldnotes-overline">SCOPE</span><button className="fieldnotes-icon-button" aria-label="Adjust scope"><SlidersHorizontal size={15} /></button></div>
              <label className="fieldnotes-filter-search"><Search size={14} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find model or case" /></label>
              <div className="fieldnotes-rail-group"><div className="fieldnotes-rail-label"><span>Model provider</span><Filter size={12} /></div>{(["all", "open", "hosted"] as const).map((filter) => <button key={filter} className={`fieldnotes-rail-choice ${providerFilter === filter ? "is-selected" : ""}`} onClick={() => setProviderFilter(filter)}><span>{filter === "all" ? "All models" : filter === "open" ? "Open weights" : "Hosted"}</span><small>{filter === "all" ? 5 : filter === "open" ? 2 : 3}</small></button>)}</div>
              <div className="fieldnotes-rail-group"><div className="fieldnotes-rail-label"><span>Evaluation suite</span><Filter size={12} /></div>{["All cases", "Networking", "Health checks", "Resources", "Scheduling", "Deployments", "Storage"].map((area) => <button key={area} className={`fieldnotes-rail-choice ${caseAreaFilter === area ? "is-selected" : ""}`} onClick={() => setCaseAreaFilter(area)}><span>{area === "All cases" ? "Shared diagnostic set" : area}</span><small>{area === "All cases" ? 8 : cases.filter((test) => test.area === area).length}</small></button>)}</div>
              <div className="fieldnotes-rail-group"><div className="fieldnotes-rail-label"><span>Recorded conditions</span><Filter size={12} /></div><div className="fieldnotes-filter-note"><span>Technique mix</span><b>varies by run</b></div><div className="fieldnotes-filter-note"><span>Time range</span><b>30 days</b></div><div className="fieldnotes-filter-note"><span>Models at full coverage</span><b>3 of 5</b></div></div>
              <div className="fieldnotes-rail-foot"><ShieldCheck size={14} /><span>Shared-case set<br /><small>8 cases · common suite</small></span></div>
            </aside>

            <section className="fieldnotes-content">
              <PageIntro kicker="EVALS / MODEL INDEX" title="Evidence, with its source." copy="Follow model performance from the shared case set to each recorded evaluation and result." meta="8 shared cases · 3 periods" />

              <section className="fieldnotes-evidence-strip" aria-label="Selected model evidence">
                <div><span>TOP MODEL / SELECTED METRIC</span><strong>{selectedMetricTop.label} <StatusMark kind="pass">{scoreText(selectedMetricTop[metric], metric)}</StatusMark></strong><small>{metricText[metric]} · same displayed eval set</small></div>
                <div><span>MOST COST-EFFICIENT</span><strong>Ember Fast <StatusMark kind="good">$0.28</StatusMark></strong><small>cost per attempt · separate ranking</small></div>
                <div><span>FASTEST RECORDED</span><strong>Ember Fast <StatusMark kind="good">75.2s</StatusMark></strong><small>mean time per attempt</small></div>
                <div><span>METRIC / SORT</span><strong>{metricText[metric]} <StatusMark kind="muted">{sortAscending ? "low → high" : "high → low"}</StatusMark></strong><small>cost, speed, and success stay distinct</small></div>
              </section>

              <div className="fieldnotes-section-top"><div><span className="fieldnotes-overline">MODEL COMPARISON</span><h2>Shared diagnostic set</h2><p>Same 8 cases · case-balanced Ground Truth · separate cost and speed dimensions</p></div><div className="fieldnotes-export"><span><GitBranch size={13} />Case-balanced</span><button aria-label="More comparison options"><ChevronDown size={14} /></button></div></div>

              <section className="fieldnotes-model-sheet">
                <div className="fieldnotes-sheet-toolbar"><div className="fieldnotes-sheet-tabs"><span className="is-active">All models <b>5</b></span><span>Compare selection</span></div><label className="fieldnotes-mini-search"><Search size={13} /><input placeholder="Filter models" value={search} onChange={(event) => setSearch(event.target.value)} /></label><button className="fieldnotes-sheet-action" onClick={() => setSortAscending((value) => !value)}><ArrowUpDown size={14} />Sort <span>{sortAscending ? "ascending" : "descending"}</span></button></div>
                <div className="fieldnotes-table-scroller"><table className="fieldnotes-model-table"><thead><tr><th>MODEL / FAMILY</th><th><button onClick={() => { onMetricChange("success"); setSortAscending(false); }}>GT SUCCESS <span className={metric === "success" ? "metric-current" : ""}>{metric === "success" ? "●" : "↕"}</span></button></th><th><button onClick={() => { onMetricChange("cost"); setSortAscending(true); }}>COST / ATTEMPT <span className={metric === "cost" ? "metric-current" : ""}>{metric === "cost" ? "●" : "↕"}</span></button></th><th><button onClick={() => { onMetricChange("speed"); setSortAscending(true); }}>SECONDS / ATTEMPT <span className={metric === "speed" ? "metric-current" : ""}>{metric === "speed" ? "●" : "↕"}</span></button></th><th>EVAL COVERAGE</th><th>PROVENANCE</th></tr></thead><tbody>{visibleModels.map((model, index) => <tr key={model.id} className={selectedModelId === model.id ? "model-row-selected" : ""} onClick={() => onModelSelect(model.id)} onKeyDown={(event) => event.key === "Enter" && onModelSelect(model.id)} tabIndex={0} aria-selected={selectedModelId === model.id}><td><span className="fieldnotes-model-name"><i style={{ background: model.color }} />{model.label}</span><small className="fieldnotes-model-family">{model.family}</small></td><td><strong className="fieldnotes-score-primary">{format(model, "success")}</strong><small><StatusMark kind={toneForRate(model.success)}>{model.success >= 75 ? "STRONG" : "IN RANGE"}</StatusMark></small></td><td>{format(model, "cost")}<small>recorded USD</small></td><td>{format(model, "speed")}<small>mean wall time</small></td><td><strong>{model.coverage}%</strong><small>{model.attempts} evaluated · {model.runs} runs</small></td><td><button className="fieldnotes-provenance" onClick={(event) => { event.stopPropagation(); onModelSelect(model.id); }} title={`Open ${model.label} provenance`}><span>8 runs</span><ChevronRight size={14} /></button><small>shared suite · demo</small></td></tr>)}</tbody></table></div>
                <div className="fieldnotes-sheet-foot"><span>Showing {visibleModels.length} of {models.length} models</span><span><CircleAlert size={13} />Incomplete coverage stays outside comparable denominators</span></div>
              </section>

              <section className="fieldnotes-review-grid">
                <article className="fieldnotes-notebook"><div className="fieldnotes-panel-head"><div><span className="fieldnotes-overline">CASE × MODEL</span><h3>Shared eval coverage</h3></div><button className="fieldnotes-icon-button" title="Filter cases"><SlidersHorizontal size={14} /></button></div><div className="fieldnotes-coverage-note"><span><i />ground-truth pass rate</span><span>select a row for its contributing run</span></div><div className="fieldnotes-matrix-scroll"><table className="fieldnotes-case-table"><thead><tr><th>CASE</th>{models.slice(0, 5).map((model) => <th key={model.id} title={model.label}>{model.label.split(" ")[0]}</th>)}</tr></thead><tbody>{visibleCases.slice(0, 8).map((test) => <tr key={test.id} onClick={() => onCaseSelect(test.id)} className={selectedCaseId === test.id ? "is-selected" : ""}><td><span>{test.label}</span><small>{test.id}</small></td>{models.map((model) => { const value = test.scores[models.indexOf(model)]; return <td key={model.id}>{value == null ? <span className="fieldnotes-heat fieldnotes-heat-unknown" aria-label={`${model.label}: unknown Ground Truth outcome`}>—</span> : <button className={`fieldnotes-heat fieldnotes-heat--${value >= 80 ? "high" : value >= 60 ? "mid" : "low"}`} onClick={(event) => { event.stopPropagation(); onCaseSelect(test.id); onModelSelect(model.id); }} aria-label={`${model.label}: illustrative ${value}%`} title={`${model.label} · illustrative ${value}%`}>{value}</button>}</td>; })}</tr>)}</tbody></table></div></article>

                <aside className="fieldnotes-selected-evidence"><div className="fieldnotes-panel-head"><div><span className="fieldnotes-overline">PROVENANCE / DRILLDOWN</span><h3>{selectedModel.label}</h3></div><span className="fieldnotes-model-avatar" style={{ color: selectedModel.color, backgroundColor: `${selectedModel.color}12` }}>{selectedModel.label.slice(0, 1)}</span></div><div className="fieldnotes-selected-metric"><span>GROUND TRUTH / SHARED SUITE</span><strong>{selectedModel.success}%</strong><small>{selectedModel.attempts} attempts · {selectedModel.coverage}% case coverage</small></div><div className="fieldnotes-run-trail"><span className="fieldnotes-overline">CONTRIBUTING EVALS</span>{evalHistory.map((run, index) => <button key={run.id} className="fieldnotes-run-item" onClick={() => onPageChange("execution")}><span className="fieldnotes-run-node">{index === 0 ? <History size={12} /> : <GitBranch size={12} />}</span><span><b>{run.id} · {run.technique}</b><small>{run.date} · {run.attempts} attempts</small><code>{run.revision}</code></span><ChevronRight size={13} /></button>)}</div><div className="fieldnotes-evidence-footer"><Code2 size={12} /><span>Scope and source revision are retained per run.<br />Unknown Ground Truth stays unknown.</span></div></aside>
              </section>
            </section>
          </div>
        )}

        {page === "execution" && (
          <section className="fieldnotes-page fieldnotes-page--execution">
            <PageIntro kicker="JOBS / TRACE" title="Execution, in sequence." copy="Follow each real phase, then open the event that needs attention." meta="single-lane serial · teardown retained" />
            <article className="fieldnotes-active-run"><div className="fieldnotes-active-run-head"><div><span className="fieldnotes-overline">CAMPAIGN / EVAL-DEMO-042</span><h2>Case run 17 <small>of 40</small></h2><p>wrong_port / stepByStep / Cedar 32B</p></div><div className="fieldnotes-run-status"><i className={live ? "fieldnotes-led fieldnotes-led--pulse" : "fieldnotes-led fieldnotes-led--paused"} />{live ? "RUNNING · SIMULATED" : "PAUSED · SIMULATED"}<button onClick={() => onLiveChange(!live)}>{live ? "Pause" : "Resume"}</button></div></div><StepTimeline active={4} /><div className="fieldnotes-run-summary"><span><b>17</b> started</span><span><b>16</b> recorded</span><span className="fieldnotes-alert-count"><b>1</b> teardown issue selected</span><button onClick={() => setEventsOpen((value) => !value)}>{eventsOpen ? "Collapse event log" : "Expand event log"}<ChevronDown size={13} /></button></div></article>

            <div className="fieldnotes-execution-grid"><section className="fieldnotes-event-pane"><div className="fieldnotes-panel-head"><div><span className="fieldnotes-overline">JOB ACTIVITY · 4M 21S</span><h3>Step-by-step trace</h3></div><button className="fieldnotes-icon-button" onClick={() => setEventsOpen((value) => !value)} aria-label={eventsOpen ? "Collapse steps" : "Expand steps"}>{eventsOpen ? "−" : "+"}</button></div><ol className="fieldnotes-event-ledger">{events.map((event, index) => <li key={`${event.time}-${index}`} className={`${index === selectedEventIndex ? "is-current" : ""} event-${event.level.toLowerCase()}`}><span className="fieldnotes-event-line" /><button className="fieldnotes-event-button" onClick={() => { setSelectedEventIndex(index); setEventsOpen(true); }}><time>{event.time}</time><span className={`fieldnotes-event-sign event-sign--${event.level.toLowerCase()}`}>{event.level === "OK" ? "✓" : event.level === "ERROR" ? "×" : event.level === "WARN" ? "!" : "·"}</span><span><small>{event.stage}</small><b>{event.message}</b>{eventsOpen && <em>{event.detail}</em>}</span><ChevronRight size={14} /></button></li>)}</ol><div className="fieldnotes-event-legend"><span><i className="event-sign--ok">✓</i>passed</span><span><i className="event-sign--warn">!</i>attention</span><span><i className="event-sign--error">×</i>error · selected</span></div></section>

              <section className="fieldnotes-log-inspector"><div className="fieldnotes-panel-head"><div><span className="fieldnotes-overline">SELECTED EVENT / OUTPUT</span><h3>{selectedEvent.stage} · {selectedEvent.time}</h3></div><button className="fieldnotes-icon-button" aria-label="Log options"><SlidersHorizontal size={14} /></button></div><div className="fieldnotes-inspector-summary"><StatusMark kind={selectedEvent.level === "ERROR" ? "attention" : selectedEvent.level === "WARN" ? "mixed" : "pass"}>{selectedEvent.level}</StatusMark><strong>{selectedEvent.message}</strong><p>{selectedEvent.detail}</p></div>{selectedEvent.level === "ERROR" && <div className="fieldnotes-repair-note"><CircleAlert size={15} /><span><b>Teardown issue needs review</b><small>Runner outcome and restoration health are separate signals. Keep the lane blocked until its checks pass.</small></span></div>}<div className="fieldnotes-command-head"><span><Terminal size={13} />REDACTED COMMAND · ILLUSTRATIVE</span><button onClick={() => onLiveChange(!live)}>{live ? "Pause follow" : "Resume follow"}</button></div><pre className="fieldnotes-command"><span>$ </span>python debug_assistant_latest/runner.py<br /><span>  </span>--lab-config <i>[selected private lane]</i> <br /><span>  </span>--output-dir <i>[private result path]</i> <br /><span>  </span>--technique stepByStep wrong_port</pre><div className="fieldnotes-log-output"><span className="fieldnotes-output-code">01</span><span>runner preflight: selected lane resolved</span><span className="fieldnotes-output-code">02</span><span>case baseline: captured before mutation</span><span className="fieldnotes-output-code">03</span><span>evaluation: Ground Truth recorded independently</span><span className="fieldnotes-output-code">04</span><span className="fieldnotes-output-error">cleanup verification: baseline check requires follow-up</span><span className="fieldnotes-output-code">05</span><span>credential output and tool arguments omitted</span></div><footer className="fieldnotes-log-footer"><span><i />{live ? "STREAM SIMULATED · AUTO-FOLLOW" : "STREAM PAUSED · CURSOR PRESERVED"}</span><button onClick={() => setEventsOpen(true)}>Jump to latest <ChevronRight size={13} /></button></footer></section></div>
          </section>
        )}

        {page === "lab" && (
          <section className="fieldnotes-page fieldnotes-page--lab">
            <PageIntro kicker="LAB / INVENTORY" title="Know what a run can touch." copy="Inventory local profiles, see shared host resources, and follow lane-linked activity." meta="read-only overview · selected lane only" />
            <div className="fieldnotes-lab-guard"><ShieldCheck size={15} /><span>All visible profiles are read-only. Run preparation and Kubernetes changes stay inside the explicitly selected private lane.</span></div>
            <ResourceTiles compact />
            <section className="fieldnotes-inventory"><div className="fieldnotes-panel-head"><div><span className="fieldnotes-overline">LOCAL CLUSTER PROFILES</span><h3>Profile inventory</h3><p>Last refreshed 1s ago · sample snapshot</p></div><div className="fieldnotes-profile-filters">{(["all", "running", "stopped"] as const).map((filter) => <button key={filter} onClick={() => setProfileFilter(filter)} className={profileFilter === filter ? "is-active" : ""}>{filter === "all" ? "All" : filter === "running" ? "Running" : "Stopped"}</button>)}</div></div><div className="fieldnotes-inventory-layout"><div className="fieldnotes-profile-list"><div className="fieldnotes-inventory-columns"><span>PROFILE / CONTEXT</span><span>STATE</span><span>NODES</span><span>WORKLOADS</span><span>PODS</span><span>RELATION</span></div>{visibleProfiles.map((profile) => <button key={profile.id} className={`fieldnotes-profile-row${profile.affected ? " is-affected" : ""}${selectedProfileId === profile.id ? " is-profile-selected" : ""}`} onClick={() => setSelectedProfileId(profile.id)}><span><b>{profile.label}</b><small>{profile.context}</small></span><StatusMark kind={profile.status === "running" ? "pass" : profile.status === "stopped" ? "muted" : "mixed"}>{profile.status === "unknown" ? "UNKNOWN" : profile.status.toUpperCase()}</StatusMark><b>{profile.nodes}</b><b>{profile.workloads}</b><b>{profile.pods}</b><span className="fieldnotes-profile-relation">{profile.id === selectedProfile.id ? "Selected for operations" : profile.affected ? "Linked to this demo job" : "Host inventory only"}</span></button>)}</div><aside className="fieldnotes-selected-lane"><div className="fieldnotes-lane-header"><span className="fieldnotes-overline">HOST / RESOURCE HISTORY</span><Pill tone="muted" dot>SAMPLE</Pill></div><h3>Two GPUs. One shared host.</h3><p>Utilization is observed at host level. Treat run attribution as confirmed only when the resource mapping proves it.</p><HostTimeline /><div className="fieldnotes-lane-callout"><Activity size={14} /><span><b>{selectedProfile.label} · {selectedProfile.status}</b><small>{selectedProfile.context} · {selectedProfile.nodes} nodes · {selectedProfile.pods} pods</small></span></div><div className="fieldnotes-lane-bottom"><span>LANE SELECTION FOR ACTIONS</span><StatusMark kind={selectedProfile.id === "research-lane" ? "pass" : "muted"}>{selectedProfile.id === "research-lane" ? "RESEARCH LANE" : "READ-ONLY"}</StatusMark></div><small className="fieldnotes-lane-note">No profile switching or pod changes are available from this read-only inventory.</small></aside></div></section>
            <section className="fieldnotes-resource-detail"><div className="fieldnotes-panel-head"><div><span className="fieldnotes-overline">HOST TELEMETRY · SAMPLE WINDOW</span><h3>Resources during the campaign</h3></div><span className="fieldnotes-stale"><i />UPDATED 5S AGO</span></div><ResourceChart metric="gpu" /><div className="fieldnotes-chart-legend"><span><i />GPU 0 utilization</span><span><i />GPU 1 utilization</span><span>Host samples are illustrative, not live</span></div></section>
          </section>
        )}
      </main>
      <footer className="fieldnotes-footer"><span>kubeLLM / experimental interface</span><span>Configured Ground Truth is authoritative · simulated interface states are labeled</span><button onClick={() => onPageChange("explorer")}>Back to evaluation index <ChevronRight size={13} /></button></footer>
    </div>
  );
};

function PillCount() {
  return <span className="fieldnotes-count">1</span>;
}

function HostTimeline() {
  return <div className="fieldnotes-host-timeline"><div className="fieldnotes-host-periods"><span>−30m</span><span>−15m</span><span>NOW</span></div><ResourceChart metric="host" compact /><div className="fieldnotes-timeline-indicator"><span><i />GPU 0 · sample</span><span><i />GPU 1 · sample</span></div></div>;
}

export default Fieldnotes;
