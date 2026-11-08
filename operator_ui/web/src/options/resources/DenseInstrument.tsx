import clsx from "clsx";
import { Cpu, HardDrive, MemoryStick, Network, TriangleAlert } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { TelemetrySample } from "@/api/types";
import { Tag, Tip } from "@/components/ui";
import { HOST } from "@/demo/lab";
import { clock } from "@/demo/ReplayBar";
import { StageFallback } from "../OptionsRoom";
import { Meter, pctText, Relation, SourceNote, Sparkline, useLab } from "./shared";

function Tile({ icon, title, meta, children, className }: { icon: ReactNode; title: string; meta?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx("flex min-w-0 flex-col gap-3 rounded-lg border border-line bg-surface p-4", className)}>
      <header className="flex items-center gap-2">
        <span className="text-fg-3">{icon}</span>
        <h3 className="text-[13px] font-medium">{title}</h3>
        {meta && <span className="ml-auto text-[12px] text-fg-3">{meta}</span>}
      </header>
      {children}
    </section>
  );
}

function Big({ value, unit, sub }: { value: string; unit?: string; sub?: ReactNode }) {
  return (
    <div>
      <div className="num text-[24px] leading-none font-medium tracking-[-0.02em]">
        {value}
        {unit && <span className="ml-1 text-[13px] font-normal text-fg-3">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-[12px] text-fg-3">{sub}</div>}
    </div>
  );
}

function LiveDenseInstrument() {
  const query = useQuery({ queryKey: ["telemetry"], queryFn: api.telemetry, refetchInterval: 2_000, staleTime: 0, retry: 0 });
  const sample = query.data;
  const [history, setHistory] = useState<TelemetrySample[]>([]);
  useEffect(() => {
    if (!sample) return;
    setHistory((current) => current.at(-1)?.sampled_at === sample.sampled_at ? current : [...current.slice(-89), sample]);
  }, [sample]);
  const bytesGiB = (value?: number | null) => value == null ? "—" : `${(value / 1024 ** 3).toFixed(1)} GiB`;
  const percent = (value?: number | null, digits = 0) => value == null || !Number.isFinite(value) ? "—" : `${value.toFixed(digits)}%`;
  const tone = sample?.status === "unavailable" || sample?.stale || sample?.status === "stale" ? "warn" : "neutral";
  const processes = sample?.processes ?? [];
  if (query.isError) return <p className="rounded-lg border border-warn/40 bg-warn-soft px-4 py-3 text-[12.5px] text-warn">Host telemetry unavailable: {query.error.message}</p>;
  if (!sample) return <div className="h-48 animate-pulse rounded-lg bg-surface" />;
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2"><Tag tone={tone}>{sample.status === "unavailable" ? "Unavailable" : sample.stale || sample.status === "stale" ? "Stale sample" : sample.status === "partial" ? "Partial sample" : "Live sample"}</Tag><span className="num text-[11.5px] text-fg-3">{new Date(sample.sampled_at).toLocaleString()}</span>{sample.reason && <span className="text-[12px] text-fg-3">{sample.reason}</span>}</div>
      <div className="grid gap-4 xl:grid-cols-12">
        <Tile icon={<Cpu className="size-4" strokeWidth={1.75} />} title="CPU" meta={`${sample.cpu.per_core.length} logical CPUs`} className="xl:col-span-7">
          <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-5"><Big value={percent(sample.cpu.total_pct, 1)} sub="total utilization" /><Sparkline values={history.map((item) => item.cpu.total_pct).filter((value): value is number => value != null)} max={100} height={44} /></div>
          <div className="grid grid-cols-8 gap-[3px] sm:grid-cols-16" role="img" aria-label={`Per-core CPU utilization for ${sample.cpu.per_core.length} logical CPUs`}>
            {sample.cpu.per_core.map((load, index) => <Tip key={index} content={`CPU ${index} · ${percent(load, 1)}`}><span className="relative block h-5 overflow-hidden rounded-[2px] bg-surface-3"><span className="absolute inset-x-0 bottom-0 transition-[height] duration-500" style={{ height: `${Math.max(0, Math.min(100, load ?? 0))}%`, background: `color-mix(in oklab, var(--fg) ${Math.round(25 + (load ?? 0) * 0.7)}%, transparent)` }} /></span></Tip>)}
          </div>
        </Tile>
        <div className="grid gap-4 xl:col-span-5">
          <Tile icon={<MemoryStick className="size-4" strokeWidth={1.75} />} title="Memory" meta={bytesGiB(sample.memory?.total_bytes)}>
            <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-5"><Big value={bytesGiB(sample.memory?.used_bytes)} sub={`${percent(sample.memory?.percent)} used`} /><Sparkline values={history.map((item) => item.memory?.used_bytes).filter((value): value is number => value != null).map((value) => value / 1024 ** 3)} max={Math.max(1, (sample.memory?.total_bytes ?? 1) / 1024 ** 3)} height={36} /></div>
            <Meter value={sample.memory?.percent ?? 0} max={100} />
            <p className="text-[12px] text-fg-3">Page cache {bytesGiB(sample.memory?.cache_bytes)} · available {bytesGiB(sample.memory?.available_bytes)}</p>
          </Tile>
          <Tile icon={<HardDrive className="size-4" strokeWidth={1.75} />} title="Disk" meta={sample.disk?.path ?? "Unavailable"}>
            <div className="flex items-end justify-between gap-4"><Big value={percent(sample.disk?.percent)} sub={`${bytesGiB(sample.disk?.used_bytes)} used · ${bytesGiB(sample.disk?.free_bytes)} free`} />{sample.disk?.percent != null && sample.disk.percent >= 90 && <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-warn"><TriangleAlert className="size-3.5" strokeWidth={2} /> Low space</span>}</div>
            <Meter value={sample.disk?.percent ?? 0} max={100} tone={sample.disk?.percent != null && sample.disk.percent >= 90 ? "warn" : "neutral"} />
            <p className="text-[12px] text-fg-3">Measured filesystem: {sample.disk?.path ?? "unavailable"}</p>
          </Tile>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(sample.gpus.length ? sample.gpus : [{ index: -1, name: "GPU inventory", utilization_pct: null, memory_total_bytes: null, memory_used_bytes: null, temperature_c: null, power_w: null, status: "unavailable" }]).map((gpu) => <Tile key={gpu.index} icon={<span className="font-mono text-[11px]">GPU</span>} title={gpu.index < 0 ? "Unavailable" : `${gpu.index} · ${gpu.name}`} meta={gpu.temperature_c == null ? gpu.status ?? "Unavailable" : `${gpu.temperature_c.toFixed(0)}°C`}>
          <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-5"><Big value={percent(gpu.utilization_pct, 1)} sub="utilization" /><Sparkline values={history.map((item) => item.gpus.find((entry) => entry.index === gpu.index)?.utilization_pct).filter((value): value is number => value != null)} max={100} height={40} /></div>
          <div className="grid gap-1.5"><div className="flex justify-between text-[12px]"><span className="text-fg-3">VRAM</span><span className="num text-fg-2">{bytesGiB(gpu.memory_used_bytes)} / {bytesGiB(gpu.memory_total_bytes)}</span></div><Meter value={gpu.memory_total_bytes ? (gpu.memory_used_bytes ?? 0) / gpu.memory_total_bytes * 100 : 0} max={100} /></div>
          <p className="mt-auto border-t border-line pt-3 text-[12px] text-fg-3">GPU process attribution is not available in this sample.</p>
        </Tile>)}
        <Tile icon={<Network className="size-4" strokeWidth={1.75} />} title="Network" meta="Not sampled"><p className="text-[12.5px] text-fg-3">The current telemetry source does not report network throughput.</p></Tile>
      </div>
      <section className="overflow-hidden rounded-lg border border-line bg-surface">
        <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3"><h3 className="text-[13px] font-medium">Processes</h3><span className="text-[12px] text-fg-3">Names and resource use only; arguments and environment are not collected</span><span className="num ml-auto text-[12px] text-fg-3">{processes.length} processes</span></header>
        <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-[12.5px]"><thead><tr className="label text-left !text-[10.5px] [&>th]:h-8 [&>th]:border-b [&>th]:border-line [&>th]:px-3 [&>th]:font-medium"><th className="!pl-4">PID</th><th>User</th><th>Process</th><th className="text-right">CPU</th><th className="text-right">Memory</th><th className="!pr-4">Relation</th></tr></thead><tbody>{processes.map((process) => <tr key={process.pid} className="border-b border-line last:border-b-0 hover:bg-surface-2/60"><td className="num py-1.5 pr-3 pl-4 text-fg-3">{process.pid}</td><td className="px-3 text-fg-2">{process.user ?? "—"}</td><td className="px-3 font-mono text-[12px] text-fg">{process.name}</td><td className="num px-3 text-right text-fg">{percent(process.cpu_pct, 1)}</td><td className="num px-3 text-right text-fg-2">{bytesGiB(process.memory_bytes)}</td><td className="pr-4 pl-3"><Tag tone={process.attribution === "lane" ? "accent" : "neutral"}>{process.attribution === "unconfirmed" ? "Unconfirmed" : process.attribution === "other" ? "Other account" : process.attribution === "shared" ? "Shared" : "Lane"}</Tag></td></tr>)}</tbody></table></div>
      </section>
      <SourceNote>Host and GPU values come from the operator's live telemetry endpoint. Trend lines begin when this page is open; only point-in-time values are persisted with active campaigns.</SourceNote>
    </div>
  );
}

export default function DenseInstrument() {
  if (api.isLive) return <LiveDenseInstrument />;
  const lab = useLab();
  if (!lab) return <StageFallback />;
  const { now, history, threads, processes } = lab;
  const busy = threads.filter((load) => load > 0.4).length;

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 xl:grid-cols-12">
        <Tile icon={<Cpu className="size-4" strokeWidth={1.75} />} title="CPU" meta={`${HOST.threads} threads · 2× Xeon Gold 6338`} className="xl:col-span-7">
          <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-5">
            <Big value={pctText(now.cpu, 1)} sub={`load ${now.load1.toFixed(2)} · ${busy} threads busy`} />
            <Sparkline values={history.map((s) => s.cpu)} max={0.25} height={44} />
          </div>
          <div className="grid grid-cols-16 gap-[3px]" role="img" aria-label={`Per-thread load, ${busy} of ${HOST.threads} threads above 40 percent`}>
            {threads.map((load, i) => (
              <Tip key={i} content={`Thread ${i} · ${pctText(load)}`}>
                <span className="relative block h-5 overflow-hidden rounded-[2px] bg-surface-3">
                  <span className="absolute inset-x-0 bottom-0 transition-[height] duration-500" style={{ height: `${Math.max(4, load * 100)}%`, background: `color-mix(in oklab, var(--fg) ${Math.round(25 + load * 70)}%, transparent)` }} />
                </span>
              </Tip>
            ))}
          </div>
        </Tile>

        <div className="grid gap-4 xl:col-span-5">
          <Tile icon={<MemoryStick className="size-4" strokeWidth={1.75} />} title="Memory" meta={`${HOST.memTotalGiB} GiB`}>
            <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-5">
              <Big value={now.memUsedGiB.toFixed(1)} unit="GiB used" sub={`${Math.round(now.memCacheGiB)} GiB page cache`} />
              <Sparkline values={history.map((s) => s.memUsedGiB)} max={16} height={36} />
            </div>
            <div className="flex h-1.5 overflow-hidden rounded-full bg-surface-3" aria-hidden>
              <span className="bg-fg-2" style={{ width: `${(now.memUsedGiB / HOST.memTotalGiB) * 100}%` }} />
              <span className="bg-fg-3/40" style={{ width: `${(now.memCacheGiB / HOST.memTotalGiB) * 100}%` }} />
            </div>
          </Tile>
          <Tile icon={<HardDrive className="size-4" strokeWidth={1.75} />} title="Root disk" meta={`${HOST.diskTotalGB} GB`}>
            <div className="flex items-end justify-between gap-4">
              <Big value="98%" sub={`${HOST.diskUsedGB} GB used · ${HOST.diskFreeGB} GB free`} />
              <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-warn">
                <TriangleAlert className="size-3.5" strokeWidth={2} /> Low space
              </span>
            </div>
            <Meter value={98} max={100} tone="warn" />
            <SourceNote>Below the 20 GiB that preparation needs on the Docker data root to start the lane's profile. A running lane is unaffected until it has to be restarted.</SourceNote>
          </Tile>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.75fr)]">
        {now.gpus.map((gpu, index) => {
          const owner = processes.find((p) => p.gpu?.index === index);
          return (
            <Tile key={index} icon={<span className="font-mono text-[11px]">GPU</span>} title={`GPU ${index} · ${HOST.gpus[index].name}`} meta={`${gpu.tempC.toFixed(0)}°C · ${gpu.powerW.toFixed(0)} W`}>
              <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-5">
                <Big value={pctText(gpu.util)} sub="utilization" />
                <Sparkline values={history.map((s) => s.gpus[index].util)} height={40} stroke={gpu.util > 0.3 ? "var(--accent)" : "var(--fg-2)"} />
              </div>
              <div className="grid gap-1.5">
                <div className="flex justify-between text-[12px]">
                  <span className="text-fg-3">VRAM</span>
                  <span className="num text-fg-2">
                    {gpu.vramGB.toFixed(1)} / {HOST.gpus[index].vramGB} GB
                  </span>
                </div>
                <Meter value={gpu.vramGB} max={HOST.gpus[index].vramGB} />
              </div>
              <div className="mt-auto border-t border-line pt-3 text-[12.5px]">
                {owner ? (
                  <div className="grid gap-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-fg">{owner.name}</span>
                      <span className="num text-fg-3">{owner.gpu?.memGB.toFixed(1)} GB</span>
                      <span className="ml-auto">
                        <Relation attribution={owner.attribution} />
                      </span>
                    </div>
                    <p className="text-fg-3">
                      {owner.attribution === "other"
                        ? "Another account's process. Not related to this campaign."
                        : "Serves the campaign's local model during its debug phase. Activity here coincides with the run; it is a shared service, so it is not attributed to the run."}
                    </p>
                  </div>
                ) : (
                  <p className="text-fg-3">No GPU processes.</p>
                )}
              </div>
            </Tile>
          );
        })}
        <Tile icon={<Network className="size-4" strokeWidth={1.75} />} title="Network" meta="host">
          <div className="grid gap-3">
            <div>
              <div className="flex justify-between text-[12px]">
                <span className="text-fg-3">Receive</span>
                <span className="num text-fg-2">{now.rxMBs.toFixed(2)} MB/s</span>
              </div>
              <Sparkline values={history.map((s) => s.rxMBs)} max={6.5} height={30} />
            </div>
            <div>
              <div className="flex justify-between text-[12px]">
                <span className="text-fg-3">Send</span>
                <span className="num text-fg-2">{now.txMBs.toFixed(2)} MB/s</span>
              </div>
              <Sparkline values={history.map((s) => s.txMBs)} max={0.5} height={30} />
            </div>
          </div>
        </Tile>
      </div>

      <section className="overflow-hidden rounded-lg border border-line bg-surface">
        <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
          <h3 className="text-[13px] font-medium">Processes</h3>
          <span className="text-[12px] text-fg-3">by CPU · names only, arguments and environment hidden</span>
          <span className="num ml-auto text-[12px] text-fg-3">sampled at {clock(lab.t)}</span>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-[12.5px]">
            <thead>
              <tr className="label text-left !text-[10.5px] [&>th]:h-8 [&>th]:border-b [&>th]:border-line [&>th]:px-3 [&>th]:font-medium">
                <th className="!pl-4">PID</th>
                <th>User</th>
                <th>Process</th>
                <th>Role</th>
                <th className="text-right">CPU</th>
                <th className="text-right">Memory</th>
                <th className="text-right">GPU</th>
                <th className="!pr-4">Relation</th>
              </tr>
            </thead>
            <tbody>
              {processes.map((p) => (
                <tr key={p.pid} className="border-b border-line last:border-b-0 hover:bg-surface-2/60">
                  <td className="num py-1.5 pr-3 pl-4 text-fg-3">{p.pid}</td>
                  <td className="px-3 text-fg-2">{p.user}</td>
                  <td className="px-3 font-mono text-[12px] text-fg">{p.name}</td>
                  <td className="max-w-[300px] truncate px-3 text-fg-2">{p.role}</td>
                  <td className="num px-3 text-right text-fg">{pctText(p.cpu, 1)}</td>
                  <td className="num px-3 text-right text-fg-2">{p.memGiB.toFixed(1)} GiB</td>
                  <td className="num px-3 text-right text-fg-2">{p.gpu ? `${p.gpu.memGB.toFixed(1)} GB · ${p.gpu.index}` : "—"}</td>
                  <td className="pr-4 pl-3">
                    <Relation attribution={p.attribution} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <SourceNote>Demo values shaped by the lab survey (Nov 1, 2026). On the lab, host metrics come from Performance Co-Pilot (pmproxy) and GPU metrics from nvidia-smi, sampled every 2 seconds, each with its timestamp and a stale state.</SourceNote>
    </div>
  );
}
