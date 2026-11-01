import { useCallback, useState } from "react";
import { surfaceDef, type OptionDef, type Surface } from "./registry";

const key = (surface: Surface) => `kubellm-option-${surface}`;

function read(surface: Surface): string | null {
  try {
    return localStorage.getItem(key(surface));
  } catch {
    return null;
  }
}

// Which option a surface page shows: the viewer's remembered pick, else the
// recommended one. A per-viewer convenience only; the decision itself is
// recorded in design-work.md.
export function useOptionChoice(surface: Surface): [OptionDef, (id: string) => void] {
  const def = surfaceDef(surface);
  const fallback = def.options.find((o) => o.recommended) ?? def.options[0];
  const [id, setId] = useState<string>(() => read(surface) ?? fallback.id);
  const choose = useCallback(
    (next: string) => {
      setId(next);
      try {
        localStorage.setItem(key(surface), next);
      } catch {
        /* storage unavailable: the pick lasts for this page only */
      }
    },
    [surface],
  );
  return [def.options.find((o) => o.id === id) ?? fallback, choose];
}
