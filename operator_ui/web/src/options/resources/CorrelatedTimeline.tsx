import { area, line } from "d3-shape";
import clsx from "clsx";
import { useMemo, useRef, useState } from "react";
import { Segmented, Tag } from "@/components/ui";
import type { DemoCampaign } from "@/demo/campaign";
import { HOST, sampleAt, type HostSample } from "@/demo/lab";
import { clock } from "@/demo/ReplayBar";
import { useReplay } from "@/demo/replay";
import { humanize } from "@/lib/cases";
import { ModelLabel } from "../execution/shared";
import { StageFallback } from "../OptionsRoom";
import { Relation, SourceNote, pctText } from "./shared";

const POINTS = 220;
const isLocal = (model: string) => model.includes(":");

interface Lane {
  id: string;
  label: string;
  value: (s: HostSample) => number;
  max: number;
  format: (v: number) => string;
  tone: string;
  note?: string;
}

const LANES: Lane[] = [
  { id: "gpu0", label: "GPU 0 utilization", value: (s) => s.gpus[0].util, max: 1, format: (v) => pctText(v), tone: "var(--fg-2)" },
  { id: "vram0", label: "GPU 0 memory", value: (s) => s.gpus[0].vramGB, max: 46, format: (v) => `${v.toFixed(1)} GB`, tone: "var(--fg-2)" },
  { id: "gpu1", label: "GPU 1 utilization", value: (s) => s.gpus[1].util, max: 1, format: (v) => pctText(v), tone: "var(--fg-3)", note: "Another account" },
  { id: "cpu", label: "CPU", value: (s) => s.cpu, max: 0.25, format: (v) => pctText(v, 1), tone: "var(--fg-2)" },
  { id: "mem", label: "Memory used", value: (s) => s.memUsedGiB, max: 16, format: (v) => `${v.toFixed(1)} GiB`, tone: "var(--fg-2)" },
  { id: "rx", label: "Network receive", value: (s) => s.rxMBs, max: 6.5, format: (v) => `${v.toFixed(2)} MB/s`, tone: "var(--fg-3)" },
];

function localDebugBands(campaign: DemoCampaign, from: number, to: number) {
  return campaign.attempts
    .filter((a) => isLocal(a.model))
    .flatMap((a) => a.phases.filter((p) => p.key === "debug").map((p) => ({ start: Math.max(from, p.start), end: Math.min(to, p.end), attempt: a.index })))
    .filter((b) => b.end > b.start);
}

function LaneChart({ lane, samples, from, span, bands, cursor }: { lane: Lane; samples: HostSample[]; from: number; span: number; bands: { start: number; end: number }[]; cursor: number | null }) {
  const h = 40;
  const x = (s: HostSample) => ((s.t - from) / span) * 100;
  const y = (v: number) => h - (Math.min(v, lane.max) / lane.max) * (h - 3) - 1;
  const linePath = line<HostSample>().x(x).y((s) => y(lane.value(s)))(samples) ?? "";
  const areaPath = area<HostSample>().x(x).y0(h).y1((s) => y(lane.value(s)))(samples) ?? "";
  return (
    <svg viewBox={`0 0 100 ${h}`} preserveAspectRatio="none" className="block h-10 w-full" aria-hidden>
      {bands.map((b, i) => (
        <rect key={i} x={((b.start - from) / span) * 100} width={((b.end - b.start) / span) * 100} y={0} height={h} fill="var(--accent-soft)" />
      ))}
      <path d={areaPath} fill={lane.tone} opacity={0.14} />
      <path d={linePath} fill="none" stroke={lane.tone} strokeWidth={1.25} vectorEffect="non-scaling-stroke" />
      {cursor !== null && <line x1={cursor * 100} x2={cursor * 100} y1={0} y2={h} stroke="var(--fg)" strokeWidth={1} vectorEffect="non-scaling-stroke" opacity={0.5} />}
    </svg>
  );
}

// Resources over the campaign's own clock, with the campaign as the top lane,
// so a viewer can see what coincides with what. Coincidence is shown as
// coincidence: nothing here attributes load to the run.
export default function CorrelatedTimeline() {
  const { campaign, t } = useReplay();
  const [range, setRange] = useState<"run" | "15m">("run");
  const [cursor, setCursor] = useState<number | null>(null);
  const plot = useRef<HTMLDivElement>(null);
  const tick = Math.floor(t / 4);

  const model = useMemo(() => {
    if (!campaign) return undefined;
    const to = Math.max(tick * 4, 60);
    const from = range === "run" ? 0 : Math.max(0, to - 900);
    const span = Math.max(1, to - from);
    const samples = Array.from({ length: POINTS }, (_, i) => sampleAt(campaign, from + (span * i) / (POINTS - 1)));
    return { from, to, span, samples, bands: localDebugBands(campaign, from, to) };
  }, [campaign, tick, range]);

  if (!campaign || !model) return <StageFallback />;
  const { from, to, span, samples, bands } = model;
  const at = cursor === null ? samples[samples.length - 1] : samples[Math.round(cursor * (POINTS - 1))];
  const atAttempt = campaign.attempts.find((a) => at.t >= a.start && at.t < a.end);
  const atPhase = atAttempt?.phases.find((p) => at.t >= p.start && at.t < p.end);

  const onMove = (event: React.PointerEvent) => {
    const rect = plot.current?.getBoundingClientRect();
    if (!rect) return;
    setCursor(Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)));
  };

  const loadedSpans = bands.length;
  const otherActive = samples.some((s) => s.gpus[1].util > 0);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-fg-2">
          Lab server and the demo campaign on one clock · {clock(from)} to {clock(to)}
        </p>
        <Segmented label="Window" value={range} onChange={setRange} options={[{ value: "run", label: "Whole campaign" }, { value: "15m", label: "Last 15 min" }]} />
      </div>

      <section className="overflow-hidden rounded-lg border border-line bg-surface">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="overflow-x-auto border-b border-line lg:border-r lg:border-b-0">
            <div className="min-w-[640px] px-4 py-3">
              <div className="grid grid-cols-[148px_minmax(0,1fr)] gap-3">
                <div className="flex items-center text-[12px] text-fg-3">Campaign</div>
                <div className="relative h-7 rounded-[3px] bg-track/60">
                  {campaign.attempts
                    .filter((a) => a.end > from && a.start < to)
                    .map((a) => (
                      <span
                        key={a.index}
                        className={clsx("absolute inset-y-[3px] rounded-[2px] border", isLocal(a.model) ? "border-accent-line bg-accent-soft" : "border-fg-3/50 bg-fg-3/25")}
                        style={{ left: `${((Math.max(a.start, from) - from) / span) * 100}%`, width: `${((Math.min(a.end, to) - Math.max(a.start, from)) / span) * 100}%` }}
                        title={`Attempt ${a.index + 1} · ${a.model} · ${a.caseId}`}
                      />
                    ))}
                </div>
              </div>
              <div ref={plot} onPointerMove={onMove} onPointerLeave={() => setCursor(null)} className="mt-1 grid gap-1">
                {LANES.map((lane) => (
                  <div key={lane.id} className="grid grid-cols-[148px_minmax(0,1fr)] items-center gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-[12px] text-fg-2">{lane.label}</div>
                      {lane.note && <div className="text-[11px] text-fg-3">{lane.note}</div>}
                    </div>
                    <LaneChart lane={lane} samples={samples} from={from} span={span} bands={bands} cursor={cursor} />
                  </div>
                ))}
              </div>
              <div className="num mt-2 grid grid-cols-[148px_minmax(0,1fr)] gap-3 text-[10.5px] text-fg-3">
                <span />
                <span className="flex justify-between">
                  <span>{clock(from)}</span>
                  <span>{clock(from + span / 2)}</span>
                  <span>{clock(to)}</span>
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-fg-3">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-4 rounded-[2px] border border-accent-line bg-accent-soft" /> Local-model attempt (served by Ollama)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-4 rounded-[2px] border border-fg-3/50 bg-fg-3/25" /> API-model attempt
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-4 rounded-[2px] bg-accent-soft" /> Local-model debug phase
                </span>
              </div>
            </div>
          </div>

          <aside className="grid content-start gap-3 p-4" aria-live="polite">
            <div className="flex items-center justify-between">
              <span className="label !text-[10px]">{cursor === null ? "Now" : "At cursor"}</span>
              <span className="num text-[12.5px] text-fg">{clock(at.t)}</span>
            </div>
            <div className="rounded-md bg-surface-2 px-3 py-2 text-[12.5px]">
              {atAttempt ? (
                <div className="grid gap-0.5">
                  <span className="flex items-center gap-1.5">
                    <span className="num text-fg-3">#{atAttempt.index + 1}</span>
                    <ModelLabel model={atAttempt.model} className="text-fg" />
                  </span>
                  <span className="text-fg-2">
                    {humanize(atAttempt.caseId)} · {atPhase?.label ?? "between phases"}
                  </span>
                </div>
              ) : (
                <span className="text-fg-3">Between attempts</span>
              )}
            </div>
            <dl className="grid gap-1.5 text-[12.5px]">
              {LANES.map((lane) => (
                <div key={lane.id} className="flex justify-between gap-3">
                  <dt className="text-fg-3">{lane.label}</dt>
                  <dd className="num text-fg">{lane.format(lane.value(at))}</dd>
                </div>
              ))}
            </dl>
          </aside>
        </div>
      </section>

      <section className="rounded-lg border border-line bg-surface">
        <header className="flex items-center gap-2 border-b border-line px-4 py-3">
          <h3 className="text-[13px] font-medium">What coincides with the campaign</h3>
          <Tag tone="accent">Demo</Tag>
        </header>
        <ul className="divide-y divide-line text-[13px]">
          <li className="grid gap-1 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div>
              <div className="text-fg">
                {loadedSpans ? `GPU 0 rises during ${loadedSpans} local-model debug ${loadedSpans === 1 ? "phase" : "phases"}` : "GPU 0 stays idle while API models run"}
              </div>
              <p className="text-fg-3">
                {loadedSpans
                  ? "Ollama keeps glm-4.7-flash loaded for five minutes after use, so memory steps up and down around those phases. Ollama is a shared service; the overlap is coincidence in time, not ownership by the run."
                  : "No local-model attempt has run in this window yet. When glm-4.7-flash's attempts start, Ollama serves it on GPU 0."}
              </p>
            </div>
            <Relation attribution="shared" />
          </li>
          <li className="grid gap-1 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div>
              <div className="text-fg">{otherActive ? "GPU 1 activity from another account" : "GPU 1 idle in this window"}</div>
              <p className="text-fg-3">{otherActive ? "A process owned by another account uses GPU 1 on its own schedule. It is unrelated to this campaign." : "No process used GPU 1 in this window."}</p>
            </div>
            <Relation attribution="other" />
          </li>
          <li className="grid gap-1 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div>
              <div className="text-fg">Setup and teardown move CPU and network</div>
              <p className="text-fg-3">Fixture images and manifests are applied and removed through the lane's Docker daemon and kubelet, which belong to the selected lane.</p>
            </div>
            <Relation attribution="lane" />
          </li>
        </ul>
      </section>
      <SourceNote>
        Demo values shaped by the lab survey (Nov 1, 2026): {HOST.threads} threads, {HOST.memTotalGiB} GiB, 2× A40. On the lab, host lanes come from Performance Co-Pilot and GPU lanes from nvidia-smi.
      </SourceNote>
    </div>
  );
}
