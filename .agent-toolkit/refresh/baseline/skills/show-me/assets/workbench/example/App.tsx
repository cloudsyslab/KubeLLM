// Starting point for a workbench game. `artifact.py workbench new <dir>` copies this
// file; replace the mechanic, keep the shape: predict -> play -> compare -> replay.
import { useRef, useState } from "react";
import { Predict, ThemeToggle, createStore, useGameLoop, useKeyPress, useStore, type PredictResult } from "@/kit";
import { Badge } from "@/ui/badge";
import { Button } from "@/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card";
import { Progress } from "@/ui/progress";

const ROUNDS = 5;
const zoneFor = (round: number) => ({ start: 0.2 + ((round * 37) % 50) / 100, width: 0.16 - round * 0.015 });
const game = createStore({ round: 0, hits: 0, position: 0, running: false, lastHit: null as boolean | null });

export default function App() {
  const [prediction, setPrediction] = useState<PredictResult | null>(null);
  const state = useStore(game);
  const zone = zoneFor(state.round);
  const time = useRef(0);
  const finished = state.round >= ROUNDS;

  useGameLoop((dt) => {
    time.current += dt * (1.4 + state.round * 0.45);
    game.set((current) => ({ ...current, position: (Math.sin(time.current) + 1) / 2 }));
  }, state.running && !finished);

  const stop = () => {
    if (!state.running || finished) return;
    const hit = state.position >= zone.start && state.position <= zone.start + zone.width;
    game.set((current) => ({ ...current, round: current.round + 1, hits: current.hits + (hit ? 1 : 0), lastHit: hit }));
  };
  useKeyPress((key) => key === " " && stop());

  const restart = () => {
    time.current = 0;
    game.set({ round: 0, hits: 0, position: 0, running: true, lastHit: null });
  };

  return (
    <main className="mx-auto grid max-w-2xl gap-6 px-4 py-10 sm:px-8 sm:py-16">
      <ThemeToggle className="fixed top-3 right-3" />
      <header className="grid gap-3">
        <p className="font-mono text-[11px] font-medium tracking-[0.08em] text-signal uppercase">Example game</p>
        <h1 className="text-5xl">Hit the zone</h1>
        <p className="text-lg text-fg-2">Stop the marker inside the zone. It speeds up and the zone shrinks every round.</p>
      </header>

      <Predict
        prompt={`How many of ${ROUNDS} rounds will you hit?`}
        choices={[
          { id: "low", label: "0–1" },
          { id: "mid", label: "2–3" },
          { id: "high", label: "4–5" },
        ]}
        onReveal={(result) => {
          setPrediction(result);
          restart();
        }}
      >
        <p>Locked in. Press space or tap Stop when the marker is inside the zone.</p>
      </Predict>

      {prediction && (
        <Card>
          <CardHeader>
            <CardTitle>{finished ? "Done" : `Round ${state.round + 1} of ${ROUNDS}`}</CardTitle>
            <CardDescription>
              Hits: <span className="font-mono text-foreground tabular-nums">{state.hits}</span>
              {state.lastHit !== null && (
                <Badge className="ml-2" variant={state.lastHit ? "good" : "bad"}>
                  {state.lastHit ? "✓ hit" : "✗ miss"}
                </Badge>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={(state.round / ROUNDS) * 100} aria-label="Rounds played" />
            <div className="relative h-14 rounded-md border bg-canvas" role="img" aria-label="Marker track with a target zone">
              {!finished && (
                <div
                  className="absolute inset-y-0 rounded-sm bg-signal-soft ring-1 ring-signal"
                  style={{ left: `${zone.start * 100}%`, width: `${zone.width * 100}%` }}
                />
              )}
              <div
                className="absolute inset-y-1.5 w-1 -translate-x-1/2 rounded-full bg-fg"
                style={{ left: `${state.position * 100}%` }}
              />
            </div>
            {finished ? (
              <div className="grid gap-3">
                <p>
                  You predicted <strong>{prediction.skipped ? "nothing" : { low: "0–1", mid: "2–3", high: "4–5" }[prediction.choice ?? "mid"]}</strong>{" "}
                  and hit <strong>{state.hits}</strong>. Most people overestimate the late rounds: the zone shrinks faster than it feels.
                </p>
                <Button variant="outline" onClick={restart} className="w-fit">
                  Play again
                </Button>
              </div>
            ) : (
              <Button variant="signal" size="lg" onClick={stop} className="w-fit">
                Stop
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
