import clsx from "clsx";
import { useMemo } from "react";
import { Tag } from "@/components/ui";
import { useReplay } from "@/demo/replay";
import { topologyAt, type Pod, type Profile } from "@/demo/topology";

export function useTopology() {
  const { campaign, t } = useReplay();
  const tick = Math.floor(t / 2);
  return useMemo(() => (campaign ? topologyAt(campaign, tick * 2) : undefined), [campaign, tick]);
}

// Pod and profile states are Kubernetes conditions, not benchmark outcomes, so
// they never use the Ground Truth green and red.
export function podTone(status: Pod["status"]) {
  if (status === "Running") return { dot: "bg-fg-2", text: "text-fg-2" };
  if (status === "ContainerCreating" || status === "Terminating") return { dot: "border border-fg-3", text: "text-fg-3" };
  return { dot: "bg-warn", text: "text-warn" };
}

export function PodStatus({ pod }: { pod: Pod }) {
  const tone = podTone(pod.status);
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-[12px] font-medium", tone.text)}>
      <span className={clsx("size-1.5 rounded-full", tone.dot)} aria-hidden />
      {pod.status}
    </span>
  );
}

export function KindTag({ kind }: { kind: Pod["kind"] }) {
  if (kind === "fixture") return <Tag tone="accent">Fixture</Tag>;
  if (kind === "leftover") return <Tag tone="warn">Leftover</Tag>;
  return <Tag>System</Tag>;
}

export function ProfileState({ profile }: { profile: Profile }) {
  const running = profile.status === "Running";
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-[12px]", running ? "text-fg-2" : "text-fg-3")}>
      <span className={clsx("size-1.5 rounded-full", running ? "bg-fg-2" : "border border-fg-3")} aria-hidden />
      {profile.status}
    </span>
  );
}
