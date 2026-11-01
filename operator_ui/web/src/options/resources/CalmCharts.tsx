import { useState, type ReactNode } from "react";
import { Segmented } from "@/components/ui";
import { HOST } from "@/demo/lab";
import { StageFallback } from "../OptionsRoom";
import { AreaChart, Meter, pctText, Relation, SourceNote, useLab } from "./shared";

function ChartPanel({ title, value, sub, legend, children }: { title: string; value: ReactNode; sub?: ReactNode; legend?: { label: string; color: string }[]; children: ReactNode }) {
  return (
    <section className="flex min-w-0 flex-col gap-3 rounded-lg border border-line bg-surface p-5">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[13px] text-fg-2">{title}</h3>
          <div className="num mt-1 text-[28px] leading-none font-medium tracking-[-0.02em]">{value}</div>
          {sub && <div className="mt-1.5 text-[12px] text-fg-3">{sub}</div>}
        </div>
        {legend && (
          <div className="grid gap-1 text-[12px] text-fg-3">
            {legend.map((item) => (
              <span key={item.label} className="flex items-center gap-1.5">
                <span className="h-0.5 w-3 rounded-full" style={{ background: item.color }} />
                {item.label}
              </span>
            ))}
          </div>
        )}
      </header>
      {children}
    </section>
  );
}

export default function CalmCharts() {
  const [range, setRange] = useState<"3m" | "15m">("3m");
  const lab = useLab(90, range === "3m" ? 2 : 10);
  const [showAll, setShowAll] = useState(false);
  if (!lab) return <StageFallback />;
  const { now, history, processes } = lab;
  const gpuColors = ["var(--accent)", "var(--fg-3)"];

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-fg-2">
          Lab server · {HOST.threads} threads · {HOST.memTotalGiB} GiB · 2× A40
        </p>
        <Segmented label="Time range" value={range} onChange={setRange} options={[{ value: "3m", label: "3 min" }, { value: "15m", label: "15 min" }]} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <ChartPanel title="CPU" value={pctText(now.cpu, 1)} sub={`load ${now.load1.toFixed(2)}`}>
          <AreaChart series={[{ label: "CPU", values: history.map((s) => s.cpu), color: "var(--fg-2)" }]} max={0.25} />
        </ChartPanel>
        <ChartPanel title="Memory used" value={`${now.memUsedGiB.toFixed(1)} GiB`} sub={`of ${HOST.memTotalGiB} GiB · ${Math.round(now.memCacheGiB)} GiB cache`}>
          <AreaChart series={[{ label: "Memory", values: history.map((s) => s.memUsedGiB), color: "var(--fg-2)" }]} max={16} />
        </ChartPanel>
        <ChartPanel title="Root disk" value={<span className="text-warn">98%</span>} sub={`${HOST.diskFreeGB} GB free · below the 20 GiB profile-start minimum`}>
          <div className="flex h-[140px] flex-col justify-end gap-2">
            <p className="text-[12.5px] text-fg-3">Unchanged over this window. Preparation needs 20 GiB free on the Docker data root to start the lane's profile.</p>
            <Meter value={HOST.diskUsedGB} max={HOST.diskTotalGB} tone="warn" className="h-2" />
            <div className="num flex justify-between text-[11.5px] text-fg-3">
              <span>{HOST.diskUsedGB} GB used</span>
              <span>{HOST.diskTotalGB} GB</span>
            </div>
          </div>
        </ChartPanel>
        <ChartPanel
          title="GPU utilization"
          value={`${pctText(now.gpus[0].util)} · ${pctText(now.gpus[1].util)}`}
          sub="GPU 0 · GPU 1"
          legend={[
            { label: "GPU 0", color: gpuColors[0] },
            { label: "GPU 1", color: gpuColors[1] },
          ]}
        >
          <AreaChart series={now.gpus.map((_, i) => ({ label: `GPU ${i}`, values: history.map((s) => s.gpus[i].util), color: gpuColors[i] }))} max={1} />
        </ChartPanel>
        <ChartPanel
          title="GPU memory"
          value={`${now.gpus[0].vramGB.toFixed(1)} · ${now.gpus[1].vramGB.toFixed(1)} GB`}
          sub="of 46 GB each"
          legend={[
            { label: "GPU 0", color: gpuColors[0] },
            { label: "GPU 1", color: gpuColors[1] },
          ]}
        >
          <AreaChart series={now.gpus.map((_, i) => ({ label: `GPU ${i} memory`, values: history.map((s) => s.gpus[i].vramGB), color: gpuColors[i] }))} max={46} />
        </ChartPanel>
        <ChartPanel
          title="Network"
          value={`${now.rxMBs.toFixed(2)} MB/s`}
          sub={`receive · send ${now.txMBs.toFixed(2)} MB/s`}
          legend={[
            { label: "Receive", color: "var(--fg-2)" },
            { label: "Send", color: "var(--fg-3)" },
          ]}
        >
          <AreaChart
            series={[
              { label: "Receive", values: history.map((s) => s.rxMBs), color: "var(--fg-2)" },
              { label: "Send", values: history.map((s) => s.txMBs), color: "var(--fg-3)" },
            ]}
            max={6.5}
          />
        </ChartPanel>
      </div>

      <section className="rounded-lg border border-line bg-surface">
        <header className="flex items-center justify-between border-b border-line px-5 py-3">
          <h3 className="text-[13px] font-medium">Top processes</h3>
          <button type="button" onClick={() => setShowAll(!showAll)} className="cursor-pointer text-[12.5px] text-fg-3 hover:text-fg">
            {showAll ? "Show top 4" : `Show all ${processes.length}`}
          </button>
        </header>
        <ul>
          {(showAll ? processes : processes.slice(0, 4)).map((p) => (
            <li key={p.pid} className="grid grid-cols-[minmax(0,1fr)_72px_auto] items-center gap-4 border-b border-line px-5 py-2.5 text-[13px] last:border-b-0 sm:grid-cols-[minmax(0,1fr)_80px_96px_auto]">
              <div className="min-w-0">
                <div className="truncate text-fg">{p.role}</div>
                <div className="font-mono text-[11.5px] text-fg-3">
                  {p.name} · {p.user} · {p.pid}
                </div>
              </div>
              <span className="num text-right text-fg-2">{pctText(p.cpu, 1)}</span>
              <span className="num hidden text-right text-fg-3 sm:block">{p.gpu ? `GPU ${p.gpu.index} · ${p.gpu.memGB.toFixed(1)} GB` : "—"}</span>
              <Relation attribution={p.attribution} />
            </li>
          ))}
        </ul>
      </section>
      <SourceNote>Demo values shaped by the lab survey (Nov 1, 2026). On the lab these come from Performance Co-Pilot and nvidia-smi.</SourceNote>
    </div>
  );
}
