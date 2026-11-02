import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, openJobEvents, type CampaignInput } from "@/api/client";
import type { JobEvent, OperatorJob, PublishPreview, TelemetrySample, TopologySnapshot } from "@/api/types";
import { PageHeader, Button, Tag } from "@/components/ui";
import { humanize } from "@/lib/cases";
import { duration } from "@/lib/format";
import type { Surface } from "./registry";

const POLL_MS = 1_500;
const LIVE_PATHS: Record<Surface, { title: string; eyebrow: string; description: string }> = {
  runs: { title: "Runs", eyebrow: "Evaluate", description: "Recorded benchmark runs and their case results." },
  compare: { title: "Compare", eyebrow: "Evaluate", description: "Compare recorded runs on their shared cases." },
  execution: { title: "Execution", eyebrow: "Operate", description: "Live campaign progress, phase events, and recorded outcomes." },
  launch: { title: "New campaign", eyebrow: "Operate", description: "Plan and explicitly start a serial campaign through the canonical runner." },
  environment: { title: "Environment", eyebrow: "Operate", description: "Check readiness of the selected private lane or request its scoped preparation." },
  jobs: { title: "Jobs", eyebrow: "Operate", description: "Read operator job history, status, and attempt outcomes." },
  publish: { title: "Publish results", eyebrow: "Operate", description: "Review the exact sanitized export before publishing it." },
  resources: { title: "Resources", eyebrow: "Lab", description: "Live host, memory, disk, GPU, and process measurements." },
  topology: { title: "Topology", eyebrow: "Lab", description: "Read-only local profile inventory and selected-lane workloads." },
  dock: { title: "Active work", eyebrow: "Operate", description: "Current operator job and progress." },
};

function useJobs() {
  return useQuery({ queryKey: ["operator-jobs"], queryFn: api.jobs, enabled: api.isLive, refetchInterval: POLL_MS, staleTime: 0, retry: 0 });
}

function useLiveQuery<T>(key: string, fn: () => Promise<T>, interval = POLL_MS) {
  return useQuery({ queryKey: [key], queryFn: fn, enabled: api.isLive, refetchInterval: interval, staleTime: 0, retry: 0 });
}

function Stamp({ value }: { value?: string | null }) {
  return <span className="num text-[11.5px] text-fg-3">{value ? new Date(value).toLocaleString() : "Time unavailable"}</span>;
}

function SampleState({ sampledAt, stale, status, reason }: { sampledAt?: string; stale?: boolean; status?: string; reason?: string | null }) {
  const unavailable = status === "unavailable";
  const partial = status === "partial";
  const isStale = stale || status === "stale";
  return (
    <div className="flex flex-wrap items-center gap-2 text-[12px]">
      <Tag tone={unavailable || partial || isStale ? "warn" : "neutral"}>{unavailable ? "Unavailable" : partial ? "Partial sample" : isStale ? "Stale sample" : "Live sample"}</Tag>
      <Stamp value={sampledAt} />
      {reason && <span className="text-fg-3">{reason}</span>}
    </div>
  );
}

function Card({ title, value, detail }: { title: string; value: string; detail?: string }) {
  return (
    <section className="grid gap-1 rounded-lg border border-line bg-surface p-4">
      <div className="label">{title}</div>
      <div className="num text-[23px] font-medium">{value}</div>
      {detail && <div className="text-[12px] text-fg-3">{detail}</div>}
    </section>
  );
}

function pct(value: number | null | undefined) {
  return value == null || !Number.isFinite(value) ? "—" : `${value.toFixed(1)}%`;
}

function bytes(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  const gib = value / (1024 ** 3);
  return `${gib.toFixed(gib >= 100 ? 0 : 1)} GiB`;
}

function age(value: string | null | undefined) {
  if (!value) return "—";
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return value;
  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1_000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function Message({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "warn" }) {
  return <p className={clsx("rounded-md border px-3 py-2 text-[12.5px]", tone === "warn" ? "border-warn/40 bg-warn-soft text-warn" : "border-line text-fg-3")}>{children}</p>;
}

function JobStatus({ job }: { job: OperatorJob }) {
  const active = ["queued", "running", "stop_requested"].includes(job.status);
  const failed = ["blocked", "failed", "interrupted"].includes(job.status);
  return <Tag tone={active ? "accent" : failed ? "warn" : "neutral"}>{job.status.replaceAll("_", " ")}</Tag>;
}

function jobTitle(job: OperatorJob) {
  return ({ readiness: "Preflight", prepare: "Preparation", campaign: "Campaign", publish: "Publication" } as const)[job.kind];
}

function latestFirst(jobs: OperatorJob[]) {
  return [...jobs].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

function targetLabel(preview: PublishPreview) {
  const target = preview.target;
  if (typeof target === "string") return target.trim() || "Target unavailable";
  if (target?.display) return target.display;
  if (!target) return preview.branch ?? "Target unavailable";
  const destination = target.worktree_path ?? target.worktree;
  const location = [target.remote, target.branch ?? preview.branch].filter(Boolean).join("/");
  const base = target.base_branch ? `based on ${target.base_branch}${target.base_sha ? ` @ ${target.base_sha}` : ""}` : "";
  return [target.kind, destination && `worktree ${destination}`, location, base].filter(Boolean).join(" · ") || "Target unavailable";
}

function useFeedback() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const run = useMutation({
    mutationFn: (action: () => Promise<OperatorJob>) => action(),
    onMutate: () => setError(""),
    onSuccess: async () => {
      await Promise.all([queryClient.invalidateQueries({ queryKey: ["operator-jobs"] }), queryClient.invalidateQueries({ queryKey: ["operator-overview"] })]);
    },
    onError: (cause) => setError(cause instanceof Error ? cause.message : "Request failed."),
  });
  return { run, error };
}

function ShellCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="grid min-w-0 gap-3 rounded-lg border border-line bg-surface p-4"><h2 className="text-[13.5px] font-medium">{title}</h2>{children}</section>;
}

function ReadinessPage() {
  const jobsQuery = useJobs();
  const overviewQuery = useLiveQuery("operator-overview", api.overview, 10_000);
  const { run, error } = useFeedback();
  const jobs = latestFirst(jobsQuery.data ?? []);
  const latest = jobs.find((job) => (job.kind === "readiness" || job.kind === "prepare") && job.result?.readiness);
  const readiness = latest?.result?.readiness;
  const fresh = overviewQuery.data?.readiness?.status === "READY";
  const readinessLabel = overviewQuery.error ? "State unavailable" : overviewQuery.isLoading ? "Checking" : fresh ? "Ready" : overviewQuery.data?.readiness?.status ?? (readiness ? "Stale" : "Not checked");
  const busy = jobsQuery.isError || jobs.some((job) => ["queued", "running", "stop_requested"].includes(job.status));
  return (
    <div className="grid gap-4">
      <ShellCard title="Selected lane readiness">
        <div className="flex flex-wrap items-center gap-2">
          <Tag tone={fresh ? "neutral" : readinessLabel === "BLOCKED" || readinessLabel === "State unavailable" ? "warn" : "neutral"}>{readinessLabel}</Tag>
          {latest && <><span className="text-[12px] text-fg-3">{jobTitle(latest)} · {latest.status}</span><Stamp value={latest.finished_at} /></>}
        </div>
        {!readiness && (jobsQuery.error || overviewQuery.error) ? <Message tone="warn">Readiness details are unavailable while the operator API is unreachable.</Message> : !readiness && <Message>Run preflight to check the explicitly selected private lane.</Message>}
        {readiness && <div className="grid gap-2">
          {readiness.checks.map((check) => <article key={check.name} className="grid gap-2 border-t border-line pt-2">
            <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{check.label}</span><Tag tone={check.status === "fail" && check.blocking ? "warn" : "neutral"}>{check.status}{check.blocking ? " · blocking" : ""}</Tag>{check.duration_ms != null && <span className="num text-[11.5px] text-fg-3">{duration(check.duration_ms / 1000)}</span>}</div>
            {check.detail && <p className="text-[12px] text-fg-2">{check.detail}</p>}
            {check.hint && <p className="text-[12px] text-warn">{check.hint}</p>}
            {check.commands?.map((command, index) => <div className="grid gap-1 rounded-md bg-bg p-2 font-mono text-[11.5px]" key={index}>
              <div className="break-all text-fg-2">{command.parent_command ?? command.command ?? "Check command"}</div>
              {command.command && command.parent_command && <div className="break-all text-fg-3">$ {command.command}</div>}
              {command.stdout && <pre className="max-h-40 overflow-auto whitespace-pre-wrap text-fg-2">{command.stdout}</pre>}
              {command.stderr && <pre className="max-h-40 overflow-auto whitespace-pre-wrap text-warn">{command.stderr}</pre>}
              <span className="text-fg-3">{command.exit_code == null ? command.note ?? "In-process check" : `exit ${command.exit_code}`}</span>
            </div>)}
          </article>)}
        </div>}
        {error && <Message tone="warn">{error}</Message>}
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" disabled={busy || jobsQuery.isLoading || overviewQuery.isLoading || run.isPending} onClick={() => run.mutate(() => api.runReadiness())}>Run preflight</Button>
          <Button disabled={busy || jobsQuery.isLoading || overviewQuery.isLoading || run.isPending} onClick={() => run.mutate(() => api.prepare())}>Prepare selected lane</Button>
        </div>
        <p className="text-[11.5px] text-fg-3">Preparation uses the runner’s repair-safe path and rechecks readiness. A fresh Ready result gates campaign launch.</p>
      </ShellCard>
      {jobsQuery.error && <Message tone="warn">{jobsQuery.error.message}</Message>}
      {overviewQuery.error && <Message tone="warn">Could not confirm whether preflight is still fresh: {overviewQuery.error.message}</Message>}
    </div>
  );
}

function LaunchPage() {
  const jobsQuery = useJobs();
  const casesQuery = useLiveQuery("operator-cases", api.cases, 60_000);
  const runsQuery = useLiveQuery("explorer", api.explorerRuns, 30_000);
  const overviewQuery = useLiveQuery("operator-overview", api.overview, 10_000);
  const { run, error } = useFeedback();
  const [cases, setCases] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [technique, setTechnique] = useState("allStepsAtOnce");
  const [repetitions, setRepetitions] = useState(1);
  const [apiModel, setApiModel] = useState("");
  const [verificationModel, setVerificationModel] = useState("");
  const jobs = jobsQuery.data ?? [];
  const fresh = overviewQuery.data?.readiness?.status === "READY";
  const busy = jobsQuery.isError || jobs.some((job) => ["queued", "running", "stop_requested"].includes(job.status));
  const availableModels = useMemo(() => [...new Set((runsQuery.data ?? []).flatMap((item) => item.models.DebugAgent))].sort(), [runsQuery.data]);
  const availableApiModels = useMemo(() => [...new Set((runsQuery.data ?? []).flatMap((item) => item.models.API))].sort(), [runsQuery.data]);
  const availableVerificationModels = useMemo(() => [...new Set((runsQuery.data ?? []).flatMap((item) => item.models.Verification))].sort(), [runsQuery.data]);
  const selected = useMemo(() => casesQuery.data?.filter((item) => cases.includes(item.id)) ?? [], [casesQuery.data, cases]);
  const planned = selected.length * models.length * repetitions;
  const toggleCase = (id: string) => setCases((old) => old.includes(id) ? old.filter((value) => value !== id) : [...old, id]);
  const toggleModel = (id: string) => setModels((old) => old.includes(id) ? old.filter((value) => value !== id) : [...old, id]);
  const start = () => {
    const input: CampaignInput = { cases, techniques: [technique], debug_models: models, api_model: apiModel, verification_model: verificationModel, repetitions };
    run.mutate(() => api.startCampaign(input));
  };
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
      <ShellCard title="Campaign plan">
        <label className="label">Debug models from recorded run history</label>
        {runsQuery.error ? <Message tone="warn">Recorded model choices unavailable: {runsQuery.error.message}</Message> : availableModels.length ? <div className="grid max-h-48 gap-1 overflow-auto sm:grid-cols-2">{availableModels.map((model) => <label key={model} className="flex items-center gap-2 rounded border border-line px-2 py-1.5 text-[12.5px]"><input type="checkbox" checked={models.includes(model)} onChange={() => toggleModel(model)} /><span className="ident truncate">{model}</span></label>)}</div> : <Message>Model choices are unavailable because no recorded DebugAgent models were returned.</Message>}
        <div className="label mt-3">Cases</div>
        {casesQuery.isLoading ? <p className="text-[12px] text-fg-3">Loading the runner case catalog…</p> : casesQuery.error ? <Message tone="warn">{casesQuery.error.message}</Message> : <div className="grid max-h-80 gap-1 overflow-auto sm:grid-cols-2">{(casesQuery.data ?? []).map((item) => <label key={item.id} className="flex items-center gap-2 rounded border border-line px-2 py-1.5 text-[12.5px]"><input type="checkbox" checked={cases.includes(item.id)} onChange={() => toggleCase(item.id)} /><span className="truncate">{item.label}</span></label>)}</div>}
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <label className="grid gap-1 text-[12px] text-fg-2">Technique<select className="h-8 rounded border border-line bg-bg px-2 text-fg" value={technique} onChange={(event) => setTechnique(event.target.value)}>{[["allStepsAtOnce", "All steps at once"], ["stepByStep", "Step by step"], ["singleAgent", "Single agent"], ["knowledgeAgentOnly", "Knowledge agent only"]].map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
          <label className="grid gap-1 text-[12px] text-fg-2">Knowledge model · optional<select className="h-8 rounded border border-line bg-bg px-2 text-fg" value={apiModel} onChange={(event) => setApiModel(event.target.value)}><option value="">Case default</option>{availableApiModels.map((model) => <option key={model} value={model}>{model}</option>)}</select></label>
          <label className="grid gap-1 text-[12px] text-fg-2">Verification model · optional<select className="h-8 rounded border border-line bg-bg px-2 text-fg" value={verificationModel} onChange={(event) => setVerificationModel(event.target.value)}><option value="">Case default</option>{availableVerificationModels.map((model) => <option key={model} value={model}>{model}</option>)}</select></label>
        </div>
        <label className="mt-3 grid max-w-48 gap-1 text-[12px] text-fg-2">Repetitions<input type="number" min={1} max={500} value={repetitions} onChange={(event) => setRepetitions(Math.min(500, Math.max(1, Number(event.target.value) || 1)))} className="h-8 rounded border border-line bg-bg px-2 text-fg" /></label>
        {error && <Message tone="warn">{error}</Message>}
      </ShellCard>
      <div className="grid content-start gap-3 rounded-lg border border-line bg-surface p-4">
        <div className="label">Plan rail</div><div className="num text-[30px] font-medium">{planned} <span className="text-[13px] text-fg-3">planned</span></div>
        <p className="text-[12px] text-fg-3">{selected.length} cases × {models.length} selected debug model{models.length === 1 ? "" : "s"} × {repetitions} repetitions · serial execution</p>
        <Tag tone={fresh ? "neutral" : "warn"}>{overviewQuery.error ? "Readiness state unavailable" : overviewQuery.isLoading ? "Checking preflight" : fresh ? "Preflight fresh" : "Fresh preflight required"}</Tag>
        {!fresh && <Button disabled={busy || jobsQuery.isLoading || run.isPending || overviewQuery.isLoading} onClick={() => run.mutate(() => api.runReadiness())}>Run preflight</Button>}
        <Button variant="primary" disabled={!fresh || jobsQuery.isError || casesQuery.isError || runsQuery.isError || overviewQuery.isError || busy || run.isPending || !cases.length || !availableModels.length || !models.length} onClick={start}>Start campaign</Button>
        {jobsQuery.error && <Message tone="warn">{jobsQuery.error.message}</Message>}
        {overviewQuery.error && <Message tone="warn">Could not confirm fresh readiness: {overviewQuery.error.message}</Message>}
      </div>
    </div>
  );
}

function EnvironmentPage() { return <ReadinessPage />; }

function Events({ job }: { job: OperatorJob }) {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [ended, setEnded] = useState(false);
  useEffect(() => {
    setEnded(false);
    if (job.kind !== "campaign") return;
    const terminal = !["queued", "running", "stop_requested"].includes(job.status);
    const close = openJobEvents(job.id, (event) => {
      setConnected(true);
      setEvents((current) => current.some((item) => item.id === event.id) ? current : [...current, event].sort((a, b) => a.id - b.id));
    }, () => setConnected(true), () => setConnected(false), terminal, () => setEnded(true));
    return close;
  }, [job.id, job.kind, job.status]);
  return <div className="grid gap-2">
    <div className="flex items-center gap-2"><span className="label">Persisted attempt events</span><Tag tone={connected ? "neutral" : ended ? "neutral" : "warn"}>{connected ? "Connected" : ended ? "Stream ended" : "Reconnecting / unavailable"}</Tag></div>
    {events.length ? <ol className="grid max-h-[520px] gap-1 overflow-auto font-mono text-[11.5px]">{events.map((event) => <li key={event.id} className="grid grid-cols-[40px_34px_56px_94px_minmax(0,1fr)] gap-2 rounded border border-line px-2 py-1.5"><span className="num text-fg-3">{duration(event.t)}</span><span className="num text-fg-3">#{event.id}</span><span className="text-fg-3">A{event.attempt + 1} · {event.phase}</span><span className="text-fg-3">{event.source} · {event.level}</span><span className={clsx("min-w-0 break-words", ["error", "fail"].includes(event.level) ? "text-warn" : "text-fg-2")}>{event.text}</span></li>)}</ol> : <Message>{connected ? "Waiting for the runner to emit its first event." : ended ? "No persisted progress events were returned." : "Events will replay after the event stream reconnects."}</Message>}
  </div>;
}

function ExecutionPage() {
  const query = useJobs();
  const jobs = latestFirst(query.data ?? []);
  const listedCampaign = jobs.find((job) => job.kind === "campaign" && ["queued", "running", "stop_requested"].includes(job.status)) ?? jobs.find((job) => job.kind === "campaign");
  const detailQuery = useQuery({ queryKey: ["operator-job", listedCampaign?.id], queryFn: () => api.job(listedCampaign!.id), enabled: api.isLive && Boolean(listedCampaign), refetchInterval: POLL_MS, staleTime: 0, retry: 0 });
  const campaign = detailQuery.data ?? listedCampaign;
  const { run, error } = useFeedback();
  if (query.error) return <Message tone="warn">{query.error.message}</Message>;
  if (!campaign) return <Message>No campaign jobs recorded yet. Plan one from New campaign.</Message>;
  const attempts = campaign.attempts ?? [];
  const active = ["queued", "running", "stop_requested"].includes(campaign.status);
  return <div className="grid gap-4">
    <ShellCard title={`Campaign ${campaign.id.slice(0, 8)}`}>
      <div className="flex flex-wrap items-center gap-2"><JobStatus job={campaign} /><span className="num text-[12px] text-fg-3">{campaign.current_index} / {campaign.total} attempts</span><Stamp value={campaign.started_at ?? campaign.created_at} /></div>
      {campaign.current_label && <p className="text-[12px] text-fg-2">{campaign.current_label}</p>}
      {detailQuery.error && <Message tone="warn">Latest job detail unavailable; showing the last jobs-list sample: {detailQuery.error.message}</Message>}
      {campaign.total > 0 && <div className="h-1.5 overflow-hidden rounded bg-surface-3" role="progressbar" aria-valuenow={campaign.current_index} aria-valuemax={campaign.total} aria-label="Completed attempts"><div className="h-full bg-accent" style={{ width: `${Math.min(100, campaign.current_index / campaign.total * 100)}%` }} /></div>}
      {active && <Button variant="secondary" disabled={run.isPending || campaign.status === "stop_requested"} onClick={() => run.mutate(() => api.stopJob(campaign.id))}>Stop after the current runner attempt</Button>}
      {error && <Message tone="warn">{error}</Message>}
    </ShellCard>
    <ShellCard title="Attempt outcomes">
      {attempts.length ? <div className="overflow-x-auto"><table className="w-full text-left text-[12px]"><thead className="text-fg-3"><tr><th className="py-1 pr-3">#</th><th className="py-1 pr-3">Case</th><th className="py-1 pr-3">Technique</th><th className="py-1 pr-3">Debug model</th><th className="py-1 pr-3">Runner</th><th className="py-1 pr-3">Ground Truth</th><th className="py-1">Verification</th></tr></thead><tbody>{attempts.map((attempt) => <tr key={attempt.sequence} className="border-t border-line"><td className="num py-1.5 pr-3">{attempt.sequence}</td><td className="py-1.5 pr-3">{humanize(attempt.case)}</td><td className="ident py-1.5 pr-3">{attempt.technique}</td><td className="ident py-1.5 pr-3">{attempt.debug_model ?? "Case default"}</td><td className="py-1.5 pr-3">{attempt.status}</td><td className="py-1.5 pr-3">{attempt.ground_truth_passed === true ? "Pass" : attempt.ground_truth_passed === false ? "Fail" : "Unknown"}</td><td className="py-1.5">{attempt.verified == null ? "Unknown" : attempt.verified ? "Agrees" : "Disagrees"}</td></tr>)}</tbody></table></div> : <Message>Attempt results appear as the canonical runner records them.</Message>}
    </ShellCard>
    <ShellCard title="Execution trace"><Events key={campaign.id} job={campaign} /></ShellCard>
  </div>;
}

function JobsPage() {
  const query = useJobs();
  const jobs = latestFirst(query.data ?? []);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const visible = jobs.filter((job) => (filter === "all" || job.kind === filter || job.status === filter) && (!search || `${job.id} ${job.current_label ?? ""} ${job.kind} ${job.status}`.toLowerCase().includes(search.toLowerCase())));
  return <div className="grid gap-4">
    <div className="flex flex-wrap gap-2"><input aria-label="Search jobs" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search jobs" className="h-8 min-w-48 rounded border border-line bg-bg px-2 text-[12.5px]" /><select aria-label="Filter jobs" value={filter} onChange={(event) => setFilter(event.target.value)} className="h-8 rounded border border-line bg-bg px-2 text-[12.5px]"><option value="all">All jobs</option><option value="campaign">Campaigns</option><option value="readiness">Preflight</option><option value="prepare">Preparation</option><option value="publish">Publication</option><option value="running">Running</option><option value="failed">Failed</option><option value="blocked">Blocked</option><option value="completed">Completed</option></select></div>
    {query.error && <Message tone="warn">Jobs endpoint unavailable; any rows below are the last cached response. {query.error.message}</Message>}
    {query.isLoading ? <Message>Loading operator jobs…</Message> : visible.length ? visible.map((job) => <article key={job.id} className="grid gap-2 rounded-lg border border-line bg-surface p-3"><div className="flex flex-wrap items-center gap-2"><span className="font-medium">{jobTitle(job)}</span><JobStatus job={job} /><span className="ident text-[11px] text-fg-3">{job.id.slice(0, 8)}</span><Stamp value={job.created_at} /></div>{job.current_label && <p className="text-[12px] text-fg-2">{job.current_label}</p>}{job.total > 0 && <span className="num text-[12px] text-fg-3">{job.current_index}/{job.total}</span>}{job.result?.reason && <p className="text-[12px] text-fg-3">{job.result.reason}</p>}</article>) : <Message>No jobs match this filter.</Message>}
  </div>;
}

function ResourcesPage() {
  const query = useLiveQuery("telemetry", api.telemetry, 2_000);
  const data = query.data as TelemetrySample | undefined;
  if (query.error) return <Message tone="warn">Telemetry unavailable: {query.error.message}</Message>;
  if (!data) return <Message>Loading live host telemetry…</Message>;
  return <div className="grid gap-4">
    <SampleState sampledAt={data.sampled_at} stale={data.stale} status={data.status} reason={data.reason} />
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <Card title="CPU" value={pct(data.cpu?.total_pct)} detail={data.cpu?.per_core?.length ? `${data.cpu.per_core.length} per-core readings` : "Per-core readings unavailable"} />
      <Card title="Memory" value={bytes(data.memory?.used_bytes)} detail={`${bytes(data.memory?.total_bytes)} total${data.memory?.percent == null ? "" : ` · ${pct(data.memory.percent)}`}`} />
      <Card title="Root disk" value={pct(data.disk?.percent)} detail={`${bytes(data.disk?.free_bytes)} free${data.disk?.free_gib == null ? "" : ` · ${data.disk.free_gib.toFixed(1)} GiB`}`} />
      <Card title="GPUs" value={data.gpu_inventory_available === false ? "—" : String(data.gpus?.length ?? 0)} detail={data.gpu_inventory_available === false ? "Device inventory unavailable" : "Devices reported by this host sample"} />
    </div>
    <ShellCard title="Per-core CPU load">
      {data.cpu?.per_core?.length ? <div className="grid grid-cols-[repeat(auto-fit,minmax(44px,1fr))] gap-1">{data.cpu.per_core.map((value, index) => <div key={index} title={`Core ${index}: ${pct(value)}`} className="grid gap-1 rounded border border-line p-1.5"><span className="text-[10px] text-fg-3">{index}</span><div className="h-10 overflow-hidden rounded bg-surface-3"><div className="mt-auto h-full bg-fg-2" style={{ transform: `translateY(${100 - Math.max(0, Math.min(100, value ?? 0))}%)` }} /></div><span className="num text-[10px] text-fg-2">{pct(value)}</span></div>)}</div> : <Message>Per-core readings unavailable.</Message>}
    </ShellCard>
    <ShellCard title="GPU devices">
        {data.gpus?.length ? <div className="grid gap-2 md:grid-cols-2">{data.gpus.map((gpu) => <article key={gpu.index} className="grid gap-2 rounded border border-line p-3"><div className="flex items-center justify-between gap-2"><span className="font-medium">GPU {gpu.index} · {gpu.name}</span><Tag>{gpu.status ?? "Available"}</Tag></div><div className="grid grid-cols-2 gap-2 text-[12px] text-fg-2"><span>Utilization · {pct(gpu.utilization_pct)}</span><span>Temperature · {gpu.temperature_c == null ? "—" : `${gpu.temperature_c} °C`}</span><span>VRAM · {bytes(gpu.memory_used_bytes)} / {bytes(gpu.memory_total_bytes)}</span><span>Power · {gpu.power_w == null ? "—" : `${gpu.power_w} W`}</span></div></article>)}</div> : <Message>{data.gpu_inventory_available === false ? "GPU telemetry is unavailable on this host." : "No GPU devices were reported in this host sample."}</Message>}
    </ShellCard>
    <ShellCard title="Processes">
      {data.processes?.length ? <div className="overflow-x-auto"><table className="w-full text-left text-[12px]"><thead className="text-fg-3"><tr><th className="py-1 pr-3">PID</th><th className="py-1 pr-3">User</th><th className="py-1 pr-3">Process</th><th className="py-1 pr-3">CPU</th><th className="py-1 pr-3">Memory</th><th className="py-1">Attribution</th></tr></thead><tbody>{data.processes.map((process) => <tr className="border-t border-line" key={process.pid}><td className="num py-1.5 pr-3">{process.pid}</td><td className="py-1.5 pr-3">{process.user ?? "—"}</td><td className="py-1.5 pr-3">{process.name}</td><td className="py-1.5 pr-3">{pct(process.cpu_pct)}</td><td className="py-1.5 pr-3">{bytes(process.memory_bytes)}</td><td className="py-1.5"><Tag tone={process.attribution === "lane" ? "accent" : "neutral"}>{process.attribution}</Tag></td></tr>)}</tbody></table></div> : <Message>{data.process_inventory_available === false ? "Process inventory is unavailable." : "No process rows were reported in this sample."}</Message>}
      <p className="text-[11.5px] text-fg-3">Shared resource activity does not establish that a process belongs to a campaign. Attribution remains unconfirmed unless ownership is known.</p>
    </ShellCard>
  </div>;
}

function TopologyPage() {
  const query = useLiveQuery("topology", api.topology, 5_000);
  const data = query.data as TopologySnapshot | undefined;
  const [search, setSearch] = useState("");
  if (query.error) return <Message tone="warn">Topology unavailable: {query.error.message}</Message>;
  if (!data) return <Message>Loading local profile inventory…</Message>;
  const chosen = data.selected_profile;
  const pods = chosen?.pods?.filter((pod) => !search || `${pod.name} ${pod.namespace} ${pod.status}`.toLowerCase().includes(search.toLowerCase())) ?? [];
  return <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
    <ShellCard title="Local profiles">
      <SampleState sampledAt={data.sampled_at} stale={data.stale} status={data.status} reason={data.reason} />
      {data.profiles.length ? <ul className="grid gap-1">{data.profiles.map((profile) => <li key={profile.name} className="flex items-center justify-between gap-2 rounded border border-line px-2 py-2 text-[12.5px]"><span className="min-w-0 truncate">{profile.name}</span><span className="flex shrink-0 items-center gap-1.5">{profile.selected && <Tag tone="accent">Selected lane</Tag>}<Tag tone={profile.status.toLowerCase() === "running" ? "neutral" : "warn"}>{profile.status}</Tag></span></li>)}</ul> : <Message>No locally discoverable profiles or profile access is unavailable.</Message>}
      <p className="text-[11.5px] text-fg-3">Workload inspection is limited to the selected private lane.</p>
    </ShellCard>
    <div className="grid content-start gap-3">
      <ShellCard title={chosen ? `Selected lane · ${chosen.name}` : "Selected lane"}>
        {!chosen ? <Message tone="warn">No selected lane inventory was returned. The app never infers a target from the current Kubernetes context.</Message> : <>
          <div className="flex flex-wrap gap-2"><Tag>{chosen.status}</Tag>{chosen.kubernetes && <Tag>Kubernetes {chosen.kubernetes}</Tag>}{chosen.driver && <Tag>{chosen.driver} driver</Tag>}</div>
          {chosen.nodes.length ? <div className="grid gap-2 sm:grid-cols-2">{chosen.nodes.map((node) => <div className="rounded border border-line p-2 text-[12px]" key={node.name}><span className="font-medium">{node.name}</span><span className="ml-2 text-fg-3">{node.status}</span>{node.ip && <span className="ml-2 ident text-fg-3">{node.ip}</span>}</div>)}</div> : <Message tone="warn">No node inventory was returned for the selected lane.</Message>}
        </>}
      </ShellCard>
      <ShellCard title="Services"><div className="grid gap-2 md:grid-cols-3">{data.services.length ? data.services.map((service) => <article key={service.name} className="grid gap-1 rounded border border-line p-2"><div className="flex items-center justify-between gap-2"><span className="font-medium text-[12.5px]">{service.name}</span><Tag>{service.status}</Tag></div>{service.detail && <span className="break-all text-[11.5px] text-fg-3">{service.detail}</span>}</article>) : <Message>No service health records were returned.</Message>}</div></ShellCard>
      <ShellCard title="Lane workloads"><input aria-label="Search workloads" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search pods" className="h-8 rounded border border-line bg-bg px-2 text-[12.5px]" />{!chosen ? <Message tone="warn">Selected lane inventory is unavailable.</Message> : chosen.pods == null ? <Message tone="warn">Pod inventory is unavailable. Check selected-lane access and retry after permissions or cluster connectivity are restored.</Message> : pods.length ? <div className="overflow-x-auto"><table className="w-full text-left text-[12px]"><thead className="text-fg-3"><tr><th className="py-1 pr-3">Namespace</th><th className="py-1 pr-3">Pod</th><th className="py-1 pr-3">Status</th><th className="py-1 pr-3">Ready</th><th className="py-1 pr-3">Restarts</th><th className="py-1">Age</th></tr></thead><tbody>{pods.map((pod) => <tr key={`${pod.namespace}/${pod.name}`} className="border-t border-line"><td className="py-1.5 pr-3">{pod.namespace}</td><td className="ident py-1.5 pr-3">{pod.name}</td><td className="py-1.5 pr-3">{pod.status}</td><td className="num py-1.5 pr-3">{pod.ready ?? "—"}</td><td className="num py-1.5 pr-3">{pod.restarts ?? "—"}</td><td className="num py-1.5">{age(pod.age)}</td></tr>)}</tbody></table></div> : <Message>{search ? "No lane workloads match this filter." : "The selected lane returned no pod records."}</Message>}</ShellCard>
    </div>
  </div>;
}

function PublishPage() {
  const query = useJobs();
  const { run, error } = useFeedback();
  const campaigns = (query.data ?? []).filter((job) => job.kind === "campaign" && !["queued", "running", "stop_requested"].includes(job.status));
  const [jobId, setJobId] = useState("");
  const [preview, setPreview] = useState<PublishPreview>();
  const [files, setFiles] = useState<Record<string, string>>({});
  const [fileErrors, setFileErrors] = useState<Record<string, string>>({});
  const [loadingPaths, setLoadingPaths] = useState<string[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [reviewedPaths, setReviewedPaths] = useState<string[]>([]);
  const [targetReviewed, setTargetReviewed] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [published, setPublished] = useState(false);
  const selected = campaigns.find((job) => job.id === jobId);
  const targetAvailable = Boolean(preview && targetLabel(preview) !== "Target unavailable");
  const allFilesReviewed = targetReviewed && targetAvailable && Boolean(preview?.files.length) && Boolean(preview?.files.every((entry) => reviewedPaths.includes(entry.path)));
  const createPreview = async () => {
    if (!selected) return;
    setPreview(undefined); setFiles({}); setFileErrors({}); setReviewedPaths([]); setTargetReviewed(false); setPreviewError(""); setPublished(false);
    setPreviewLoading(true);
    try { setPreview(await api.publishPreview(selected.id)); }
    catch (cause) { setPreview(undefined); setPreviewError(cause instanceof Error ? cause.message : "Preview is unavailable."); }
    finally { setPreviewLoading(false); }
  };
  const loadFile = async (path: string) => {
    if (!selected) return;
    setLoadingPaths((current) => [...new Set([...current, path])]);
    setFileErrors((current) => ({ ...current, [path]: "" }));
    try {
      const result = await api.publishPreviewFile(selected.id, path);
      setFiles((current) => ({ ...current, [path]: result.content }));
    } catch (cause) {
      setFileErrors((current) => ({ ...current, [path]: cause instanceof Error ? cause.message : "File contents are unavailable." }));
    } finally { setLoadingPaths((current) => current.filter((item) => item !== path)); }
  };
  const toggleReviewed = (path: string, checked: boolean) => setReviewedPaths((current) => checked ? [...new Set([...current, path])] : current.filter((item) => item !== path));
  const send = () => {
    if (!preview || !selected) return;
    run.mutate(() => api.publish(selected.id, preview.preview_token), { onSuccess: () => setPublished(true) });
  };
  return <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
    <ShellCard title="Review campaign export">
      <label className="grid max-w-xl gap-1 text-[12px] text-fg-2">Ended campaign<select className="h-8 rounded border border-line bg-bg px-2 text-fg" value={jobId} onChange={(event) => { setJobId(event.target.value); setPreview(undefined); setFiles({}); setFileErrors({}); setReviewedPaths([]); setTargetReviewed(false); setPreviewError(""); setPublished(false); }}><option value="">Choose a campaign</option>{campaigns.map((job) => <option key={job.id} value={job.id}>{job.id.slice(0, 8)} · {job.current_index}/{job.total} attempts · {job.status}</option>)}</select></label>
      {query.error && <Message tone="warn">Campaign jobs unavailable: {query.error.message}</Message>}
      {query.isLoading && <Message>Loading campaign jobs…</Message>}
      {!query.error && !query.isLoading && !campaigns.length && <Message>No ended campaign jobs are available to preview.</Message>}
      <Button disabled={!selected || query.isError || previewLoading || run.isPending} onClick={createPreview}>{previewLoading ? "Preparing preview…" : "Prepare exact preview"}</Button>
      {preview && <>
        <div className="flex flex-wrap gap-2"><Tag>Preview ready</Tag>{preview.expires_at && <Stamp value={preview.expires_at} />}</div>
        <p className="break-all text-[12px] text-fg-2">Target: <span className="ident">{targetLabel(preview)}</span></p>
        {preview.attempts_recorded != null && <p className="text-[12px] text-fg-2">Campaign results · {preview.attempts_recorded}/{preview.attempts_planned ?? "?"} attempts recorded · Ground Truth {preview.ground_truth_passed ?? "—"}/{preview.ground_truth_known ?? "—"} passed · Verification {preview.verifier_agrees ?? "—"}/{preview.verifier_comparable ?? "—"} agree · {preview.attempts_excluded ?? 0} excluded · {preview.attempts_unstarted ?? 0} unstarted</p>}
        {preview.files.length ? <div className="grid gap-2">{preview.files.map((entry) => <article key={entry.path} className="grid gap-2 rounded border border-line p-2">
          <div className="flex flex-wrap items-center justify-between gap-2"><span className="ident min-w-0 break-all text-[12px]">{entry.path}{entry.status && <span className="ml-2 text-fg-3">{entry.status}</span>}</span><Button disabled={Object.hasOwn(files, entry.path) || loadingPaths.includes(entry.path)} onClick={() => void loadFile(entry.path)}>{loadingPaths.includes(entry.path) ? "Loading…" : Object.hasOwn(files, entry.path) ? "Content loaded" : "Load reviewed content"}</Button></div>
          <span className="num text-[10.5px] text-fg-3">{entry.bytes == null ? "Size unavailable" : `${entry.bytes} bytes`}{entry.sha256 ? ` · SHA-256 ${entry.sha256}` : ""}</span>
          {fileErrors[entry.path] && <Message tone="warn">{fileErrors[entry.path]}</Message>}
          {Object.hasOwn(files, entry.path) && <><pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded border border-line bg-bg p-3 text-[11.5px]">{files[entry.path]}</pre><label className="flex items-start gap-2 text-[12px] text-fg-2"><input type="checkbox" checked={reviewedPaths.includes(entry.path)} onChange={(event) => toggleReviewed(entry.path, event.target.checked)} /><span>I reviewed this file’s exact preview content.</span></label></>}
        </article>)}</div> : <Message tone="warn">The preview returned no files to review.</Message>}
        {!targetAvailable && <Message tone="warn">The preview did not return a publication target, so publishing is disabled.</Message>}
        <label className="flex items-start gap-2 border-t border-line pt-3 text-[12px] text-fg-2"><input type="checkbox" checked={targetReviewed} onChange={(event) => setTargetReviewed(event.target.checked)} /><span>I reviewed the results summary and publication target above.</span></label>
        <p className="text-[11.5px] text-fg-3">Review the results summary, destination, and every preview file before publishing.</p>
        <Button variant="primary" disabled={!allFilesReviewed || run.isPending || published} onClick={send}>{published ? "Publish job started" : "Publish reviewed export"}</Button>
      </>}
      {previewError && <Message tone="warn">{previewError}</Message>}
      {published && <Message>Publication job accepted. Follow its actual status in Jobs.</Message>}
      {error && <Message tone="warn">{error}</Message>}
    </ShellCard>
    <div className="grid content-start gap-2 rounded-lg border border-line bg-surface p-4"><div className="label">Publication behavior</div><p className="text-[12px] text-fg-2">The backend commits reviewed paths in its isolated results worktree and reports the target before the publish action.</p><p className="text-[11.5px] text-fg-3">Campaign outcomes, Ground Truth, and Verification remain distinct in the receipt.</p></div>
  </div>;
}

export default function LiveSurface({ surface }: { surface: Surface }) {
  if (!api.isLive) return null;
  const meta = LIVE_PATHS[surface];
  let body: React.ReactNode;
  switch (surface) {
    case "environment": body = <EnvironmentPage />; break;
    case "launch": body = <LaunchPage />; break;
    case "execution": body = <ExecutionPage />; break;
    case "jobs": body = <JobsPage />; break;
    case "resources": body = <ResourcesPage />; break;
    case "topology": body = <TopologyPage />; break;
    case "publish": body = <PublishPage />; break;
    case "dock": body = <ExecutionPage />; break;
    case "runs":
    case "compare":
      return null;
  }
  return <div className="grid gap-6"><PageHeader eyebrow={meta.eyebrow} title={meta.title} description={meta.description} />{body}</div>;
}
