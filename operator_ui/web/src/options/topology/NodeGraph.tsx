import "@xyflow/react/dist/style.css";
import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import clsx from "clsx";
import { useMemo, useState } from "react";
import { Tag } from "@/components/ui";
import type { Pod, Profile } from "@/demo/topology";
import { useTheme } from "@/lib/theme";
import { StageFallback } from "../OptionsRoom";
import { KindTag, PodStatus, ProfileState, podTone, useTopology } from "./shared";

type Tone = "default" | "selected" | "fixture" | "leftover" | "muted";
interface CardData extends Record<string, unknown> {
  kind: string;
  title: string;
  subtitle?: string;
  status?: string;
  statusDot?: string;
  tone: Tone;
  detail: { label: string; value: string }[];
  note?: string;
  pod?: Pod;
  profile?: Profile;
}

function CardNode({ data, selected }: NodeProps<Node<CardData>>) {
  return (
    <div
      className={clsx(
        "w-[188px] rounded-md border bg-surface px-3 py-2 shadow-[0_1px_0_var(--line)] transition-colors",
        data.tone === "selected" && "border-accent-line",
        data.tone === "fixture" && "border-accent-line bg-accent-soft",
        data.tone === "leftover" && "border-warn/40",
        data.tone === "muted" && "border-line opacity-70",
        data.tone === "default" && "border-line-strong",
        selected && "ring-2 ring-fg ring-offset-1 ring-offset-bg",
      )}
    >
      <Handle type="target" position={Position.Left} className="!size-1.5 !min-h-0 !min-w-0 !border-0 !bg-line-strong" />
      <div className="label !text-[9.5px]">{data.kind}</div>
      <div className="truncate font-mono text-[12px] text-fg">{data.title}</div>
      {(data.status || data.subtitle) && (
        <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-fg-3">
          {data.statusDot && <span className={clsx("size-1.5 rounded-full", data.statusDot)} />}
          <span className="truncate">{data.status ?? data.subtitle}</span>
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!size-1.5 !min-h-0 !min-w-0 !border-0 !bg-line-strong" />
    </div>
  );
}

const nodeTypes = { card: CardNode };

function build(profiles: Profile[], services: { name: string; detail: string; status: string; uptime: string }[]) {
  const nodes: Node<CardData>[] = [];
  const edges: Edge[] = [];
  const add = (id: string, x: number, y: number, data: CardData) => nodes.push({ id, type: "card", position: { x, y }, data, draggable: false });
  const link = (source: string, target: string, dashed = false) =>
    edges.push({ id: `${source}-${target}`, source, target, style: { stroke: "var(--line-strong)", strokeWidth: 1.25, strokeDasharray: dashed ? "4 4" : undefined } });

  add("host", 0, 250, { kind: "Host", title: "lab server", subtitle: "Ubuntu 22.04 · 2× A40", tone: "default", detail: [{ label: "Threads", value: "128" }, { label: "Memory", value: "755 GiB" }, { label: "Root disk", value: "98% used · 12 GB free" }] });
  add("docker", 215, 150, { kind: "Runtime", title: "dockerd", subtitle: "minikube profiles", tone: "default", detail: [{ label: "Driver", value: "docker" }] });
  link("host", "docker");

  services.forEach((service, i) => {
    add(`svc-${i}`, 215, 360 + i * 76, { kind: "Service", title: service.name, status: service.status, statusDot: "bg-fg-2", tone: "default", detail: [{ label: "Where", value: service.detail }, { label: "Up", value: service.uptime }] });
    link("host", `svc-${i}`);
  });

  profiles.forEach((profile, i) => {
    const id = `profile-${profile.name}`;
    add(id, 430, 20 + i * 76, {
      kind: profile.defaultContext ? "Profile · default context" : "Profile",
      title: profile.name,
      status: profile.status,
      statusDot: profile.status === "Running" ? "bg-fg-2" : "border border-fg-3",
      tone: profile.selected ? "selected" : "muted",
      detail: [
        { label: "Kubernetes", value: profile.kubernetes },
        { label: "Access", value: profile.selected ? "Selected lane: actions allowed" : "Read-only status" },
      ],
      profile,
    });
    link("docker", id);
  });

  const lane = profiles.find((p) => p.selected)!;
  add("node", 645, 20, { kind: "Node", title: lane.nodes[0].name, status: lane.nodes[0].status, statusDot: "bg-fg-2", tone: "selected", detail: [{ label: "Internal IP", value: lane.nodes[0].ip ?? "—" }] });
  link(`profile-${lane.name}`, "node");
  services.forEach((_, i) => i < 2 && link(`svc-${i}`, `profile-${lane.name}`, true));

  const namespaces = [...new Set(lane.pods.map((p) => p.namespace))];
  let podY = -40;
  namespaces.forEach((ns, n) => {
    const nsId = `ns-${ns}`;
    const pods = lane.pods.filter((p) => p.namespace === ns);
    add(nsId, 860, n === 0 ? 0 : 280, { kind: "Namespace", title: ns, subtitle: `${pods.length} pods`, tone: "default", detail: [{ label: "Pods", value: String(pods.length) }] });
    link("node", nsId);
    if (pods.every((p) => p.kind === "system")) {
      add(`pods-${ns}`, 1075, 280, { kind: "Pods", title: `${pods.length} system pods`, status: pods.every((p) => p.status === "Running") ? "All Running" : "Check pods", statusDot: "bg-fg-2", tone: "default", detail: pods.map((p) => ({ label: p.name, value: p.status })) });
      link(nsId, `pods-${ns}`);
      return;
    }
    pods.forEach((pod) => {
      const id = `pod-${pod.name}`;
      add(id, 1075, podY, {
        kind: pod.kind === "fixture" ? "Pod · fixture" : pod.kind === "leftover" ? "Pod · leftover" : "Pod",
        title: pod.name,
        status: `${pod.status} · ${pod.ready}`,
        statusDot: podTone(pod.status).dot,
        tone: pod.kind === "fixture" ? "fixture" : pod.kind === "leftover" ? "leftover" : "default",
        detail: [
          { label: "Ready", value: pod.ready },
          { label: "Restarts", value: pod.restarts.toLocaleString() },
          { label: "Age", value: pod.age },
        ],
        note: pod.note,
        pod,
      });
      link(nsId, id);
      podY += 76;
    });
  });
  return { nodes, edges };
}

export default function NodeGraph() {
  const topology = useTopology();
  const [theme] = useTheme();
  const [selectedId, setSelectedId] = useState<string>("profile-minh-lane");
  const graph = useMemo(() => (topology ? build(topology.profiles, topology.services) : undefined), [topology]);
  if (!topology || !graph) return <StageFallback />;
  const selected = graph.nodes.find((n) => n.id === selectedId) ?? graph.nodes.find((n) => n.data.tone === "fixture") ?? graph.nodes[0];
  const nodes = graph.nodes.map((n) => ({ ...n, selected: n.id === selected.id }));

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="h-[600px] overflow-hidden rounded-lg border border-line bg-bg">
        <ReactFlow
          nodes={nodes}
          edges={graph.edges}
          nodeTypes={nodeTypes}
          colorMode={theme}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          minZoom={0.3}
          nodesConnectable={false}
          elementsSelectable
          onNodeClick={(_, node) => setSelectedId(node.id)}
          proOptions={{ hideAttribution: true }}
          style={{ background: "var(--bg)" }}
        >
          <Background gap={20} size={1} color="var(--grid)" />
          <Controls showInteractive={false} className="!overflow-hidden !rounded-md !border !border-line !shadow-none [&>button]:!border-line [&>button]:!bg-surface [&>button]:!fill-fg-2" />
        </ReactFlow>
      </div>
      <aside className="grid content-start gap-3 rounded-lg border border-line bg-surface p-4">
        <div className="label !text-[10px]">{selected.data.kind}</div>
        <div className="font-mono text-[15px] font-medium break-all">{selected.data.title}</div>
        {selected.data.pod && (
          <div className="flex flex-wrap items-center gap-2">
            <PodStatus pod={selected.data.pod} />
            <KindTag kind={selected.data.pod.kind} />
          </div>
        )}
        {selected.data.profile && (
          <div className="flex flex-wrap items-center gap-2">
            <ProfileState profile={selected.data.profile} />
            {selected.data.profile.selected ? <Tag tone="accent">Selected lane</Tag> : <Tag>Read-only</Tag>}
          </div>
        )}
        <dl className="grid gap-1.5 text-[12.5px]">
          {selected.data.detail.map((d) => (
            <div key={d.label} className="grid grid-cols-[96px_minmax(0,1fr)] gap-2">
              <dt className="truncate text-fg-3">{d.label}</dt>
              <dd className="text-fg">{d.value}</dd>
            </div>
          ))}
        </dl>
        {selected.data.note && <p className="text-[12.5px] leading-relaxed text-fg-2">{selected.data.note}</p>}
        <p className="border-t border-line pt-3 text-[12px] text-fg-3">Select any node. Demo state shaped by the lab survey (Nov 1, 2026).</p>
      </aside>
    </div>
  );
}
