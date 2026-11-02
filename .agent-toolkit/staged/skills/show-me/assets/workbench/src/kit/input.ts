import { useEffect, useRef, type RefObject } from "react";

/** Live set of held keys (KeyboardEvent.key, lowercased; space is " "). Read it inside the game loop. */
export function useKeys(): RefObject<Set<string>> {
  const keys = useRef(new Set<string>());
  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      if (event.key === " " || event.key.startsWith("Arrow")) event.preventDefault();
      keys.current.add(event.key.toLowerCase());
    };
    const up = (event: KeyboardEvent) => keys.current.delete(event.key.toLowerCase());
    const clear = () => keys.current.clear();
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", clear);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", clear);
    };
  }, []);
  return keys;
}

/** Calls onPress(key) once per key press (not while held). Handy for "press space to stop". */
export function useKeyPress(onPress: (key: string) => void) {
  const handler = useRef(onPress);
  useEffect(() => {
    handler.current = onPress;
  });
  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      if (event.repeat) return;
      if (event.key === " ") event.preventDefault();
      handler.current(event.key.toLowerCase());
    };
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, []);
}

export type PointerState = { x: number; y: number; down: boolean; inside: boolean };

/** Pointer position relative to an element (in its CSS pixels) plus button state; works for mouse and touch. */
export function usePointer<T extends HTMLElement>(target: RefObject<T | null>): RefObject<PointerState> {
  const state = useRef<PointerState>({ x: 0, y: 0, down: false, inside: false });
  useEffect(() => {
    const element = target.current;
    if (!element) return;
    const move = (event: PointerEvent) => {
      const rect = element.getBoundingClientRect();
      state.current.x = event.clientX - rect.left;
      state.current.y = event.clientY - rect.top;
      state.current.inside = true;
    };
    const press = (event: PointerEvent) => {
      move(event);
      state.current.down = true;
    };
    const release = () => {
      state.current.down = false;
    };
    const leave = () => {
      state.current.inside = false;
    };
    element.addEventListener("pointermove", move);
    element.addEventListener("pointerdown", press);
    element.addEventListener("pointerleave", leave);
    window.addEventListener("pointerup", release);
    return () => {
      element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerdown", press);
      element.removeEventListener("pointerleave", leave);
      window.removeEventListener("pointerup", release);
    };
  }, [target]);
  return state;
}
