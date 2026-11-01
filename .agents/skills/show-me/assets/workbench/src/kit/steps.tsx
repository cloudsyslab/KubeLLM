import { useCallback, useEffect, useState } from "react";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { Button } from "@/ui/button";

/** Index state for a step-through explanation, with arrow-key navigation. */
export function useSteps(count: number, { keyboard = true } = {}) {
  const [index, setIndex] = useState(0);
  const go = useCallback((target: number) => setIndex(Math.max(0, Math.min(count - 1, target))), [count]);
  useEffect(() => {
    if (!keyboard) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "ArrowRight") go(index + 1);
      if (event.key === "ArrowLeft") go(index - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, index, keyboard]);
  return { index, go, next: () => go(index + 1), prev: () => go(index - 1), isFirst: index === 0, isLast: index === count - 1 };
}

export function StepNav({ steps, count }: { steps: ReturnType<typeof useSteps>; count: number }) {
  return (
    <div className="flex items-center gap-3">
      <Button variant="outline" size="icon" onClick={steps.prev} disabled={steps.isFirst} aria-label="Previous step">
        <ChevronLeftIcon />
      </Button>
      <span className="text-sm text-muted-foreground tabular-nums">
        {steps.index + 1} / {count}
      </span>
      <Button variant="outline" size="icon" onClick={steps.next} disabled={steps.isLast} aria-label="Next step">
        <ChevronRightIcon />
      </Button>
    </div>
  );
}
