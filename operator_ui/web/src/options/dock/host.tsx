import { Suspense } from "react";
import { useOptionChoice } from "../choice";
import { GLOBAL, type DockSlot } from "./index";

// Renders the picked active-work option in its slot on every page.
export function DockHost({ slot }: { slot: DockSlot }) {
  const [option] = useOptionChoice("dock");
  const entry = GLOBAL[option.id];
  if (!entry || entry.slot !== slot) return null;
  const Component = entry.component;
  return (
    <Suspense fallback={null}>
      <Component />
    </Suspense>
  );
}
