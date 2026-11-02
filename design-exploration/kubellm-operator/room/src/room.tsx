import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Activity, ArrowUpRight, Check, ChevronDown, Compass, ExternalLink, Layers, Monitor, Moon, Network, Play, ShieldCheck, Sparkles, Square, Terminal } from "lucide-react";
import type { DirectionId, DirectionProps, MetricId, PageId } from "./domain";
import { illustrativeNotice } from "./data";
import braintrustExample from "./assets/references/braintrust-experiment-comparison.png";
import modalLogsExample from "./assets/references/modal-logs-v2.gif";
import modalLogsFrame from "./assets/references/modal-logs-frame.png";
import "./references.css";
const Atlas = lazy(() => import("./directions/Atlas").then((module) => ({ default: module.Atlas })));
const Fieldnotes = lazy(() => import("./directions/Fieldnotes"));
const Signal = lazy(() => import("./directions/Signal").then((module) => ({ default: module.Signal })));

const directionInfo: Record<DirectionId, { name: string; title: string; strap: string; qualities: string[]; marker: string }> = {
  atlas: { name: "Atlas", title: "A clearer picture of model performance.", strap: "Analysis-first", qualities: ["Open evaluation explorer", "Comparative charts", "Case-level evidence"], marker: "A" },
  signal: { name: "Signal", title: "When the lab is working, you can see it.", strap: "Operations-first", qualities: ["Run stays in view", "Terminal and timeline", "Lab resource strip"], marker: "B" },
  fieldnotes: { name: "Fieldnotes", title: "Every score has a source.", strap: "Evidence-first", qualities: ["Dense result tables", "Clear denominators", "Run provenance"], marker: "C" },
};

interface UrlState { direction: DirectionId | null; page: PageId; metric: MetricId }

function readParams(): UrlState {
  const params = new URLSearchParams(window.location.search);
  const rawDirection = params.get("direction");
  const direction = rawDirection === "atlas" || rawDirection === "signal" || rawDirection === "fieldnotes" ? rawDirection : null;
  const rawPage = params.get("page");
  const page: PageId = rawPage === "execution" || rawPage === "lab" ? rawPage : "explorer";
  const rawMetric = params.get("metric");
  const metric: MetricId = rawMetric === "cost" || rawMetric === "speed" ? rawMetric : "success";
  return { direction, page, metric };
}

function writeParams(next: Partial<UrlState>) {
  const current = readParams();
  const url = new URL(window.location.href);
  const value = { ...current, ...next };
  if (value.direction) url.searchParams.set("direction", value.direction);
  else url.searchParams.delete("direction");
  url.searchParams.set("page", value.page);
  url.searchParams.set("metric", value.metric);
  window.history.pushState(null, "", `${url.pathname}?${url.searchParams.toString()}`);
}

function DirectionGlyph({ id }: { id: DirectionId }) {
  const glyphs = { atlas: <Activity size={16} />, signal: <Terminal size={16} />, fieldnotes: <Layers size={16} /> };
  return <span className={`direction-glyph glyph-${id}`}>{glyphs[id]}</span>;
}

function DesignRoom({
  direction,
  onSelect,
}: {
  direction: (id: DirectionId) => void;
  onSelect: (id: DirectionId, page: PageId) => void;
}) {
  const directions: DirectionId[] = ["atlas", "signal", "fieldnotes"];
  return (
    <div className="room-index">
      <header className="board-top"><div className="board-brand"><span className="board-brand-mark">K</span><span><b>KubeLLM</b><small>OPERATOR DIRECTIONS</small></span></div><div className="board-top-center"><span className="board-eyebrow"><Compass size={13} /> DIRECTIONS · ROUND 01</span><span className="preview-safe"><i /> DESIGN PREVIEW</span></div><a className="board-top-link" href="#reference-heading">Reference study <ChevronDown size={13} /></a></header>
      <main className="board-main">
        <section className="board-intro"><span className="board-kicker">KUBERNETES EVALS, MADE VISIBLE</span><h1>Three ways into the same lab.</h1><p>Explore the same evaluation data, live run, and A40 lab in three interactive directions. Pick a direction to see the whole workspace at full size.</p><div className="board-metrics"><span><strong>03</strong> distinct compositions</span><i /><span><strong>01</strong> shared sample dataset</span><i /><span><strong>02</strong> A40s · actual host</span></div></section>
        <section className="direction-card-grid" aria-label="Three design directions">{directions.map((id, index) => { const info = directionInfo[id]; return <button className={`direction-card direction-card-${id}`} key={id} onClick={() => direction(id)}><div className="direction-card-top"><DirectionGlyph id={id} /><span className="direction-index">DIRECTION 0{index + 1}</span><ArrowUpRight size={15} className="direction-open" /></div><span className="direction-strap">{info.strap}</span><strong className="direction-title">{info.title}</strong><ul>{info.qualities.map((quality) => <li key={quality}><Check size={12} />{quality}</li>)}</ul><div className="direction-mini" aria-hidden="true"><DirectionThumbnail id={id} /></div><span className="direction-cta">Explore direction <span>→</span></span></button>; })}</section>
        <section className="reference-study" aria-labelledby="reference-heading"><div className="reference-study-heading"><span className="reference-small-icon"><Sparkles size={14} /></span><div><h2 id="reference-heading">Reference study</h2><p>Patterns that shaped these directions, with source status called out.</p></div></div><div className="reference-study-grid">
          <article className="reference-study-card reference-study-aa"><div className="reference-study-meta"><span className="reference-index">01</span><span>MODEL COMPARISON</span><a href="https://artificialanalysis.ai/models/comparisons" target="_blank" rel="noreferrer" aria-label="Artificial Analysis model comparisons"><ExternalLink size={13} /></a></div><div className="reference-metric-pattern"><div><b>QUALITY</b><span>intelligence</span></div><div><b>SPEED</b><span>tokens per second</span></div><div><b>PRICE</b><span>per 1M tokens</span></div></div><h3>Artificial Analysis</h3><p>Leaderboard and comparison dimensions reviewed from public pages. Pattern summary, not a captured screen.</p></article>
          <article className="reference-study-card"><div className="reference-study-meta"><span className="reference-index">02</span><span>EXECUTION STREAM</span><a href="https://modal.com/blog/modal-product-updates-feb-2025" target="_blank" rel="noreferrer" aria-label="Modal product updates source"><ExternalLink size={13} /></a></div><a className="reference-motion-link" href={modalLogsExample} target="_blank" rel="noreferrer" aria-label="Open the original Modal execution logs animation"><img className="reference-study-image modal-reference-poster" src={modalLogsFrame} alt="Representative frame from Modal's official animated execution logs example" loading="lazy" /><span><Play size={11} fill="currentColor" /> Open original animation</span></a><h3>Modal</h3><p>Historical vendor media, not a fresh capture. Open its animation to inspect the execution log example.</p></article>
          <article className="reference-study-card"><div className="reference-study-meta"><span className="reference-index">03</span><span>EVAL COMPARISON</span><a href="https://www.braintrust.dev/articles/llm-eval-pipeline-github-actions" target="_blank" rel="noreferrer" aria-label="Braintrust comparison example source"><ExternalLink size={13} /></a></div><img className="reference-study-image braintrust-reference" src={braintrustExample} alt="Braintrust vendor article example showing a model by metric comparison table" loading="lazy" /><h3>Braintrust</h3><p>Static comparison figure in an official article, not a live application capture. Useful for connecting summary scores to eval results.</p></article>
        </div></section>
        <footer className="board-foot"><span>Shared: five model profiles · eight cases · one run story · one lab</span><span>Illustrative data is always marked</span></footer>
      </main>
    </div>
  );
}

function DirectionThumbnail({ id }: { id: DirectionId }) {
  return <div className={`mini-frame mini-${id}`}><div className="mini-bar"><i /><i /><i /></div><div className="mini-inside"><div className="mini-sidebar" /><div className="mini-content"><div className="mini-title" /><div className="mini-stat-row"><i /><i /><i /></div><div className="mini-main-grid"><i /><i /></div><div className="mini-lines"><i /><i /><i /><i /></div></div></div></div>;
}

function DesignTopbar({
  direction,
  page,
  onIndex,
  onPage,
  onMode,
  live,
  viewport,
  onViewport,
}: {
  direction: DirectionId;
  page: PageId;
  onIndex: () => void;
  onPage: (page: PageId) => void;
  onMode: (live: boolean) => void;
  live: boolean;
  viewport: "wide" | "tablet" | "mobile";
  onViewport: (viewport: "wide" | "tablet" | "mobile") => void;
}) {
  const info = directionInfo[direction];
  return <header className="direction-topbar"><button className="direction-brand" onClick={onIndex} title="Back to all directions"><span className={`board-brand-mark brand-${direction}`}>K</span><span><b>KubeLLM</b><small>{info.name.toUpperCase()} · DESIGN DIRECTION</small></span></button><nav className="direction-nav" aria-label="Preview pages">{([ ["explorer", <Activity size={14} />, "Models"], ["execution", <Terminal size={14} />, "Execution"], ["lab", <Network size={14} />, "Lab"] ] as const).map(([target, icon, label]) => <button key={target} className={page === target ? "active" : ""} onClick={() => onPage(target)}>{icon}{label}</button>)}</nav><div className="direction-toolbar"><span className="cluster-top-indicator"><span className="cluster-glyph">⌘</span> Research lab <i>·</i> 2 × A40</span><span className="toolbar-separator" /><div className="mode-switch" role="group" aria-label="Preview state"><button className={live ? "active mode-live" : ""} onClick={() => onMode(true)}><Play size={11} fill="currentColor" />Running</button><button className={!live ? "active mode-failure" : ""} onClick={() => onMode(false)}><Square size={10} fill="currentColor" />Failure</button></div><span className="toolbar-separator" /><div className="viewport-switch" role="group" aria-label="Preview width"><button title="Wide viewport" aria-pressed={viewport === "wide"} className={viewport === "wide" ? "active" : ""} onClick={() => onViewport("wide")}><Monitor size={13} /></button><button title="Tablet viewport" aria-pressed={viewport === "tablet"} className={viewport === "tablet" ? "active" : ""} onClick={() => onViewport("tablet")}><Layers size={13} /></button><button title="Mobile viewport" aria-pressed={viewport === "mobile"} className={viewport === "mobile" ? "active" : ""} onClick={() => onViewport("mobile")}><span className="mobile-device-icon" /></button></div><a className="exit-direction" href={`?direction=${direction}&page=${page}`} aria-label="Reset direction preview"><Moon size={13} /></a></div></header>;
}

function DirectionWrapper({ direction, viewport, children }: { direction: DirectionId; viewport: "wide" | "tablet" | "mobile"; children: React.ReactNode }) {
  return <div className={`direction-viewport viewport-${viewport} direction-viewport-${direction}`}><div className="direction-viewport-inner">{children}</div></div>;
}

export function Room() {
  const [urlState, setUrlState] = useState<UrlState>(readParams);
  const [live, setLive] = useState(true);
  const [viewport, setViewport] = useState<"wide" | "tablet" | "mobile">("wide");
  const [metric, setMetric] = useState<MetricId>(urlState.metric);
  const [selectedModelId, setSelectedModelId] = useState("cedar-32");
  const [selectedCaseId, setSelectedCaseId] = useState("wrong_port");

  useEffect(() => { const listener = () => { const next = readParams(); setUrlState(next); setMetric(next.metric); }; window.addEventListener("popstate", listener); return () => window.removeEventListener("popstate", listener); }, []);

  const navigate = useCallback((next: Partial<UrlState>) => {
    writeParams(next);
    const value = { ...readParams(), ...next };
    setUrlState(value);
    if (value.metric) setMetric(value.metric);
  }, []);

  const onSelectDirection = useCallback((direction: DirectionId) => {
    setSelectedModelId("cedar-32");
    setSelectedCaseId("wrong_port");
    navigate({ direction, page: "explorer" });
  }, [navigate]);

  const onPageChange = useCallback((page: PageId) => navigate({ page }), [navigate]);
  const onMetricChange = useCallback((next: MetricId) => navigate({ metric: next }), [navigate]);

  const props: DirectionProps = { page: urlState.page, onPageChange, metric, onMetricChange, selectedModelId, onModelSelect: setSelectedModelId, selectedCaseId, onCaseSelect: setSelectedCaseId, live, onLiveChange: setLive };
  let content: React.ReactNode = null;
  if (urlState.direction === "atlas") content = <Atlas {...props} />;
  else if (urlState.direction === "signal") content = <Signal {...props} />;
  else if (urlState.direction === "fieldnotes") content = <Fieldnotes {...props} />;

  return <div className="design-room"><div className="room-simulation-ribbon"><span><span className="ribbon-signal" /><b>DESIGN ROOM</b></span><span>{illustrativeNotice}</span><span className="room-ribbon-right"><ShieldCheck size={12} />PREVIEW ONLY · NO LAB ACTIONS</span></div>
    {!urlState.direction ? <DesignRoom direction={onSelectDirection} onSelect={onSelectDirection} /> : <><DesignTopbar direction={urlState.direction} page={urlState.page} onIndex={() => navigate({ direction: null, page: "explorer" })} onPage={onPageChange} onMode={setLive} live={live} viewport={viewport} onViewport={setViewport} /><DirectionWrapper direction={urlState.direction} viewport={viewport}><Suspense fallback={<div className="direction-loading" role="status">Loading direction preview…</div>}>{content}</Suspense></DirectionWrapper><div className="preview-bottom-bar"><span><b>{directionInfo[urlState.direction].name}</b><span>Direction {urlState.direction === "atlas" ? "01" : urlState.direction === "signal" ? "02" : "03"} of 03</span></span><button onClick={() => navigate({ direction: null, page: "explorer" })}>Compare directions <ArrowUpRight size={13} /></button><span className="preview-source-note">{illustrativeNotice}</span></div></>}
  </div>;
}
