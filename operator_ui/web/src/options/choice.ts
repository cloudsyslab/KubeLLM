import { useCallback, useEffect, useState } from "react";
import { surfaceDef, type OptionDef, type Surface } from "./registry";

const key = (surface: Surface) => `kubellm-option-${surface}`;

export function read(surface: Surface): string | null {
  try {
    return localStorage.getItem(key(surface));
  } catch {
    return null;
  }
}

const EVENT = "kubellm-option-change";

export function recommended(surface: Surface): OptionDef {
  const def = surfaceDef(surface);
  return def.options.find((o) => o.recommended) ?? def.options[0];
}

export function pickOf(surface: Surface): OptionDef {
  const def = surfaceDef(surface);
  const id = read(surface);
  return def.options.find((o) => o.id === id) ?? recommended(surface);
}

export function writeChoice(surface: Surface, id: string | null) {
  try {
    if (id === null) localStorage.removeItem(key(surface));
    else localStorage.setItem(key(surface), id);
  } catch {
    /* storage unavailable: the pick lasts for this page only */
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { surface, id } }));
}

// Which option a surface page shows: the viewer's remembered pick, else the
// recommended one. A per-viewer convenience only; the decision itself is
// recorded in design-work.md. Picks made elsewhere (the pick sheet, the room)
// update every mounted reader.
export function useOptionChoice(surface: Surface): [OptionDef, (id: string) => void] {
  const [option, setOption] = useState<OptionDef>(() => pickOf(surface));
  useEffect(() => {
    const sync = () => setOption(pickOf(surface));
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, [surface]);
  const choose = useCallback((next: string) => writeChoice(surface, next), [surface]);
  return [option, choose];
}
