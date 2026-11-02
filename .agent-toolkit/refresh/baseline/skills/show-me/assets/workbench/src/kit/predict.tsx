import { useState, type ReactNode } from "react";
import { Button } from "@/ui/button";
import { cn } from "@/lib/utils";

export type PredictChoice = { id: string; label: ReactNode };
export type PredictResult = { choice: string | null; guess: string; skipped: boolean };

/**
 * Predict first, then reveal. The learner commits to a choice (or writes a guess)
 * before `children` (the answer) appears. Omit `correct` when the prediction is about
 * the learner themself, e.g. "how many will you get right?", and compare later.
 */
export function Predict({
  prompt,
  choices = [],
  correct,
  freeText = false,
  onReveal,
  children,
  className,
}: {
  prompt: ReactNode;
  choices?: PredictChoice[];
  correct?: string;
  freeText?: boolean;
  onReveal?: (result: PredictResult) => void;
  children?: ReactNode;
  className?: string;
}) {
  const [choice, setChoice] = useState<string | null>(null);
  const [guess, setGuess] = useState("");
  const [revealed, setRevealed] = useState<null | "guessed" | "skipped">(null);
  const open = (skipped: boolean) => {
    if (revealed) return;
    setRevealed(skipped ? "skipped" : "guessed");
    onReveal?.({ choice, guess, skipped });
  };
  return (
    <section className={cn("grid gap-4 rounded-md border border-dashed border-signal/60 bg-signal-soft/50 p-5", className)}>
      <p className="font-mono text-[11px] font-medium tracking-[0.08em] text-signal uppercase">Predict first</p>
      <div className="text-lg leading-snug tracking-tight text-fg">{prompt}</div>
      {choices.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {choices.map((option) => {
            const picked = option.id === choice;
            const right = revealed && correct === option.id;
            const wrong = revealed && picked && correct !== undefined && correct !== option.id;
            return (
              <button
                key={option.id}
                type="button"
                aria-pressed={picked}
                disabled={revealed !== null}
                onClick={() => setChoice(option.id)}
                className={cn(
                  "min-h-10 rounded-md border border-input bg-transparent px-4 py-2 text-left text-sm transition-colors hover:bg-accent",
                  picked && "border-signal bg-signal-soft",
                  right && "border-good",
                  wrong && "border-bad",
                )}
              >
                {option.label}
                {right && <span className="ml-2 font-semibold text-good">✓ right</span>}
                {wrong && <span className="ml-2 font-semibold text-bad">✗ your guess</span>}
              </button>
            );
          })}
        </div>
      )}
      {freeText && (
        <textarea
          value={guess}
          disabled={revealed !== null}
          onChange={(event) => setGuess(event.target.value)}
          placeholder="Your guess, in a sentence"
          className="min-h-20 rounded-md border border-input bg-background p-3 text-sm"
        />
      )}
      {revealed === null ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="signal" disabled={!choice && !guess.trim()} onClick={() => open(false)}>
            Lock in and reveal
          </Button>
          <button type="button" onClick={() => open(true)} className="text-sm text-muted-foreground underline">
            Skip
          </button>
        </div>
      ) : (
        children && <div className="grid gap-2 border-t pt-4 text-fg-2">{children}</div>
      )}
    </section>
  );
}
