import { useEffect, useRef } from "react";

/**
 * Calls step(dt, elapsed) once per animation frame while `running` is true.
 * dt is in seconds and capped at 1/20 so a backgrounded tab never jumps the game.
 */
export function useGameLoop(step: (dt: number, elapsed: number) => void, running = true) {
  const stepRef = useRef(step);
  useEffect(() => {
    stepRef.current = step;
  });
  useEffect(() => {
    if (!running) return;
    let frame = 0;
    let last = performance.now();
    let elapsed = 0;
    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 1 / 20);
      last = now;
      elapsed += dt;
      stepRef.current(dt, elapsed);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [running]);
}
