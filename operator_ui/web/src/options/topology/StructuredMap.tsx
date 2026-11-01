import clsx from "clsx";
import { ChevronRight, Info } from "lucide-react";
import { useState } from "react";
import { Tag, Tip } from "@/components/ui";
import type { Pod } from "@/demo/topology";
import { StageFallback } from "../OptionsRoom";
import { KindTag, PodStatus, ProfileState, useTopology } from "./shared";

function PodRow({ pod }: { pod: Pod }) {
  return (
    <li className={clsx("grid gap-1 px-4 py-2.5", pod.kind === "fixture" && "bg-accent-soft")}>
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 sm:grid-cols-[minmax(0,1fr)_150px_52px_64px_44px_auto]">
        <span className="truncate font-mono text-[12.5px] text-fg">{pod.name}</span>
        <span className="hidden sm:block">
          <PodStatus pod={pod} />
        </span>
        <span className="num hidden text-[12px] text-fg-2 sm:block">{pod.ready}</span>
        <span className="num hidden text-right text-[12px] text-fg-2 sm:block">{pod.restarts.toLocaleString()}↻</span>
        <span className="num hidden text-right text-[12px] text-fg-3 sm:block">{pod.age}</span>
        <span className="justify-self-end">
          <KindTag kind={pod.kind} />
        </span>
      </div>
      <div className="sm:hidden">
        <PodStatus pod={pod} />
      </div>
      {pod.note && (
        <p className="flex gap-1.5 text-[12px] leading-relaxed text-fg-3">
          <Info className="mt-[3px] size-3 shrink-0" strokeWidth={2} />
          {pod.note}
        </p>
      )}
    </li>
  );
}

export default function StructuredMap() {
  const topology = useTopology();
  const [systemOpen, setSystemOpen] = useState(false);
  if (!topology) return <StageFallback />;
  const lane = topology.profiles.find((p) => p.selected)!;
  const others = topology.profiles.filter((p) => !p.selected);
  const namespaces = [...new Set(lane.pods.map((p) => p.namespace))];
  const system = lane.pods.filter((p) => p.kind === "system");

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-line bg-surface px-4 py-3 text-[13px]">
        <span className="flex items-center gap-2">
          <span className="size-1.5 rounded-full bg-accent" aria-hidden />
          <span className="text-fg-3">Selected lane</span>
          <span className="font-mono text-fg">minh-lane</span>
          <span className="text-fg-3">via ~/.config/kubellm/lanes/minh.json</span>
        </span>
        <Tip content="The default kubectl context points at a stopped profile. KubeLLM never infers its target from it; actions use the explicit lane selector only.">
          <span className="flex items-center gap-2">
            <span className="text-fg-3">Default kubectl context</span>
            <span className="font-mono text-fg-2">minikube</span>
            <Tag>Not used</Tag>
          </span>
        </Tip>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="overflow-hidden rounded-lg border border-accent-line bg-surface">
          <header className="grid gap-3 border-b border-line px-4 py-3.5 sm:grid-cols-[minmax(0,1fr)_auto]">
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="font-mono text-[15px] font-medium">{lane.name}</h3>
                <ProfileState profile={lane} />
                <Tag tone="accent">Selected</Tag>
              </div>
              <p className="mt-1 text-[12.5px] text-fg-3">
                minikube · {lane.driver} · Kubernetes {lane.kubernetes} · actions confined to this lane
              </p>
            </div>
            <div className="text-[12.5px] sm:text-right">
              <div className="text-fg-3">Node</div>
              <div className="font-mono text-fg">
                {lane.nodes[0].name} <span className="text-fg-2">· {lane.nodes[0].status}</span>
              </div>
              <div className="num text-fg-3">{lane.nodes[0].ip}</div>
            </div>
          </header>
          {namespaces.map((ns) => {
            const pods = lane.pods.filter((p) => p.namespace === ns);
            const isSystem = pods.every((p) => p.kind === "system");
            return (
              <div key={ns} className="border-b border-line last:border-b-0">
                <div className="flex items-center gap-2 bg-surface-2/50 px-4 py-2 text-[12.5px]">
                  <span className="text-fg-3">namespace</span>
                  <span className="font-mono text-fg">{ns}</span>
                  <span className="num text-fg-3">· {pods.length} pods</span>
                  {isSystem && (
                    <button type="button" onClick={() => setSystemOpen(!systemOpen)} aria-expanded={systemOpen} className="ml-auto inline-flex cursor-pointer items-center gap-1 text-fg-3 hover:text-fg">
                      {system.every((p) => p.status === "Running") ? "All Running" : "Check pods"}
                      <ChevronRight className={clsx("size-3.5 transition-transform", systemOpen && "rotate-90")} strokeWidth={2} />
                    </button>
                  )}
                </div>
                {(!isSystem || systemOpen) && (
                  <ul className="divide-y divide-line">
                    {pods.map((pod) => (
                      <PodRow key={pod.name} pod={pod} />
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </section>

        <div className="grid content-start gap-4">
          <section className="rounded-lg border border-line bg-surface">
            <header className="border-b border-line px-4 py-3">
              <h3 className="text-[13px] font-medium">Other profiles</h3>
              <p className="mt-0.5 text-[12px] text-fg-3">Read-only. Status only; their workloads are not queried.</p>
            </header>
            <ul className="divide-y divide-line">
              {others.map((profile) => (
                <li key={profile.name} className="flex items-center gap-3 px-4 py-2.5 text-[13px]">
                  <span className="font-mono text-fg">{profile.name}</span>
                  {profile.defaultContext && <Tag>Default context</Tag>}
                  <span className="ml-auto">
                    <ProfileState profile={profile} />
                  </span>
                </li>
              ))}
            </ul>
          </section>
          <section className="rounded-lg border border-line bg-surface">
            <header className="border-b border-line px-4 py-3">
              <h3 className="text-[13px] font-medium">Lane services</h3>
            </header>
            <ul className="divide-y divide-line">
              {topology.services.map((service) => (
                <li key={service.name} className="grid gap-0.5 px-4 py-2.5 text-[13px]">
                  <div className="flex items-center gap-2">
                    <span className="text-fg">{service.name}</span>
                    <span className="ml-auto inline-flex items-center gap-1.5 text-[12px] text-fg-2">
                      <span className="size-1.5 rounded-full bg-fg-2" aria-hidden />
                      {service.status}
                    </span>
                  </div>
                  <div className="flex justify-between gap-3 font-mono text-[11.5px] text-fg-3">
                    <span className="truncate">{service.detail}</span>
                    <span>{service.uptime}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
      <p className="text-[12px] leading-relaxed text-fg-3">
        Demo state shaped by the lab survey (Nov 1, 2026). On the lab, the selected lane is read through its own kubeconfig; the fixture pod follows the demo campaign's current attempt.
      </p>
    </div>
  );
}
