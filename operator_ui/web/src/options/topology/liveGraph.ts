import type { TelemetrySample, TopologySnapshot } from "@/api/types";
import { HEALTH, type Health, type Rollup, type TopoNode, type TopologyGraph } from "@/demo/topologyGraph";

const blankCounts = (): Record<Health, number> => ({ healthy: 0, degraded: 0, failing: 0, "expected-broken": 0, leftover: 0, stopped: 0, unknown: 0 });
const idPart = (value: string) => value.trim().replace(/[^A-Za-z0-9_.-]+/g, "_");

function statusHealth(status: string): Health {
  const value = status.toLowerCase();
  if (value.includes("unknown") || value.includes("not sampled")) return "unknown";
  if (value.includes("crash") || value.includes("error") || value.includes("failed") || value.includes("notready") || value.includes("unavailable") || value.includes("unhealthy")) return "failing";
  if (value.includes("pending") || value.includes("partial") || value.includes("degraded") || value.includes("terminating")) return "degraded";
  if (value.includes("stopped") || value.includes("exited")) return "stopped";
  if (value.includes("healthy") || value.includes("ready") || value.includes("running")) return "healthy";
  return "unknown";
}

function podHealth(status: string, ready?: string | null): Health {
  const state = statusHealth(status);
  if (state !== "healthy") return state;
  if (!ready) return "unknown";
  const match = ready.match(/^(\d+)\/(\d+)$/);
  if (!match) return "unknown";
  const current = Number(match[1]);
  const wanted = Number(match[2]);
  return wanted > 0 && current === wanted ? "healthy" : current > 0 ? "degraded" : "failing";
}

function node(params: Omit<TopoNode, "active">): TopoNode {
  return { ...params, active: false };
}

function summarize(nodes: TopoNode[], reason: string): Rollup {
  const counts = blankCounts();
  const attention: string[] = [];
  for (const item of nodes) {
    counts[item.health] += 1;
    if (HEALTH[item.health].attention) attention.push(item.id);
  }
  const health: Health = counts.failing ? "failing" : counts.degraded ? "degraded" : counts.unknown ? "unknown" : counts.healthy ? "healthy" : counts.stopped ? "stopped" : "unknown";
  return { health, reason, counts, total: nodes.length, attention, explained: [] };
}

/** Convert the real inventory into containment only; this API does not report dependency edges. */
export function buildLiveGraph(snapshot: TopologySnapshot, telemetry?: TelemetrySample): TopologyGraph {
  const nodes: TopoNode[] = [];
  const selected = snapshot.selected_profile;
  const profileId = selected ? `profile:${idPart(selected.name)}` : undefined;
  const hostFacts = [
    { label: "Sampled", value: telemetry?.sampled_at ?? snapshot.sampled_at },
    { label: "CPU", value: telemetry?.cpu.total_pct == null ? "Unavailable" : `${telemetry.cpu.total_pct.toFixed(1)}%` },
    { label: "Memory", value: telemetry?.memory?.percent == null ? "Unavailable" : `${telemetry.memory.percent.toFixed(1)}% used` },
    { label: "Disk", value: telemetry?.disk ? `${telemetry.disk.path} · ${telemetry.disk.free_gib?.toFixed(1) ?? "?"} GiB free` : "Unavailable" },
  ];
  nodes.push(node({ id: "host", kind: "host", kindLabel: "Lab host", name: "Lab server", health: "unknown", status: "Resource telemetry is sampled separately", reason: "Resource values are measurements; they are not a host health verdict.", scope: "shared", tags: ["read-only"], facts: hostFacts }));

  for (const profile of snapshot.profiles) {
    const selectedProfile = profile.selected && selected;
    const status = selectedProfile ? selected!.status : profile.status;
    const health = statusHealth(status);
    nodes.push(node({
      id: `profile:${idPart(profile.name)}`,
      kind: "profile",
      kindLabel: "Kubernetes profile",
      name: profile.name,
      ident: profile.name,
      parent: "host",
      health,
      status,
      reason: profile.selected ? "Status from the explicitly selected private lane." : "Other profile; no live status probe is performed for this profile.",
      scope: profile.selected ? "lane" : "other",
      tags: profile.selected ? ["selected-lane", "read-only"] : ["read-only"],
      facts: [{ label: "Selected", value: profile.selected ? "Yes" : "No" }],
    }));
  }

  if (selected && profileId && !nodes.some((item) => item.id === profileId)) {
    nodes.push(node({ id: profileId, kind: "profile", kindLabel: "Kubernetes profile", name: selected.name, ident: selected.name, parent: "host", health: statusHealth(selected.status), status: selected.status, reason: "Status from the explicitly selected private lane.", scope: "lane", tags: ["selected-lane", "read-only"], facts: [{ label: "Selected", value: "Yes" }] }));
  }
  if (selected && profileId) {
    for (const item of selected.nodes) {
      const health = statusHealth(item.status);
      nodes.push(node({ id: `node:${idPart(item.name)}`, kind: "k8s-node", kindLabel: "Kubernetes node", name: item.name, ident: item.ip ?? undefined, parent: profileId, health, status: item.status, reason: health === "healthy" ? "The selected kubeconfig reports this node Ready." : `The selected kubeconfig reports ${item.status}.`, scope: "lane", tags: ["selected-lane", "read-only"], facts: [...(item.ip ? [{ label: "Internal IP", value: item.ip }] : []), { label: "Node status", value: item.status }] }));
    }
    const pods = selected.pods ?? [];
    const namespaces = [...new Set(pods.map((item) => item.namespace || "default"))].sort();
    for (const namespace of namespaces) {
      const namespaceId = `namespace:${idPart(namespace)}`;
      const inNamespace = pods.filter((item) => (item.namespace || "default") === namespace);
      nodes.push(node({ id: namespaceId, kind: "namespace", kindLabel: "Namespace", name: namespace, parent: profileId, health: "unknown", status: `${inNamespace.length} reported pods`, reason: "Namespace membership is derived from the selected lane's pod inventory; namespace health is not independently reported.", scope: "lane", tags: ["selected-lane", "read-only"], facts: [{ label: "Reported pods", value: String(inNamespace.length) }] }));
      for (const pod of inNamespace) {
        const health = podHealth(pod.status, pod.ready);
        nodes.push(node({
          id: `pod:${idPart(namespace)}:${idPart(pod.name)}`,
          kind: "pod",
          kindLabel: pod.kind ? `${pod.kind} pod` : "Pod",
          name: pod.name,
          ident: pod.name,
          parent: namespaceId,
          health,
          status: [pod.status, pod.ready].filter(Boolean).join(" · "),
          reason: pod.note ?? (health === "healthy" ? "The selected lane reports this pod Running and all containers Ready." : `Observed pod state: ${pod.status}${pod.ready ? ` · ${pod.ready} ready` : ""}.`),
          scope: "lane",
          tags: ["selected-lane", "read-only"],
          facts: [
            { label: "Namespace", value: namespace },
            ...(pod.ready ? [{ label: "Ready", value: pod.ready }] : []),
            ...(pod.restarts != null ? [{ label: "Restarts", value: String(pod.restarts) }] : []),
            ...(pod.age ? [{ label: "Created", value: pod.age }] : []),
          ],
        }));
      }
    }
  }

  for (const service of snapshot.services) {
    const health = snapshot.stale || snapshot.status === "stale" ? "unknown" : statusHealth(service.status);
    nodes.push(node({ id: `service:${idPart(service.name)}`, kind: "service", kindLabel: "Lane service", name: service.name, ident: service.detail ?? undefined, parent: "host", health, status: service.status, reason: service.detail ?? "Service status from the selected-lane inventory.", scope: "lane", tags: ["selected-lane", "read-only"], facts: [...(service.uptime ? [{ label: "Uptime", value: service.uptime }] : []), ...(service.detail ? [{ label: "Source", value: service.detail }] : [])] }));
  }
  if (telemetry) for (const gpu of telemetry.gpus) {
    nodes.push(node({ id: `gpu:${gpu.index}`, kind: "gpu", kindLabel: "GPU", name: gpu.name, ident: `GPU ${gpu.index}`, parent: "host", health: "unknown", status: gpu.status ?? "Measured", reason: "Resource use is measured; no health state is inferred from utilization, temperature, or power.", scope: "shared", tags: ["read-only"], facts: [
      { label: "Utilization", value: gpu.utilization_pct == null ? "Unavailable" : `${gpu.utilization_pct.toFixed(1)}%` },
      { label: "Memory", value: gpu.memory_total_bytes == null ? "Unavailable" : `${((gpu.memory_used_bytes ?? 0) / 1024 ** 3).toFixed(1)} / ${(gpu.memory_total_bytes / 1024 ** 3).toFixed(1)} GiB` },
      { label: "Temperature", value: gpu.temperature_c == null ? "Unavailable" : `${gpu.temperature_c.toFixed(1)}°C` },
      { label: "Power", value: gpu.power_w == null ? "Unavailable" : `${gpu.power_w.toFixed(1)} W` },
    ] }));
  }

  const byId = new Map(nodes.map((item) => [item.id, item]));
  const children = new Map<string, string[]>();
  for (const item of nodes) if (item.parent) children.set(item.parent, [...(children.get(item.parent) ?? []), item.id]);
  const rollups = new Map<string, Rollup>();
  const descendants = (id: string): TopoNode[] => (children.get(id) ?? []).flatMap((child) => [byId.get(child)!, ...descendants(child)]);
  for (const [id] of children) {
    const nested = descendants(id);
    rollups.set(id, summarize(nested, `${nested.length} reported child components.`));
  }
  const laneNodes = nodes.filter((item) => item.scope === "lane" && item.kind !== "namespace");
  const lane = summarize(laneNodes, selected ? `Selected profile ${selected.name}; ${laneNodes.length} lane components in the current read-only inventory.` : "Selected lane inventory is unavailable.");
  return {
    t: Date.parse(snapshot.sampled_at) / 1000 || 0,
    nodes,
    edges: [],
    byId,
    children,
    rollups,
    campaignStatus: "completed",
    traffic: { label: "Traffic paths are not included in the live inventory.", paths: [] },
    lane,
    relationshipsKnown: false,
  };
}

export function healthForPod(status: string, ready?: string | null): Health {
  return podHealth(status, ready);
}
