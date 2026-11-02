import clsx from "clsx";
import { Pause, Play, RotateCcw } from "lucide-react";
import { Slider, Switch } from "radix-ui";
import { Tag, Tip } from "@/components/ui";
import { runDate } from "@/lib/format";
import { SPEEDS, useReplay } from "./replay";

export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

function Toggle({ label, hint, checked, onChange }: { label: string; hint: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <Tip content={hint}>
      <label className="flex cursor-pointer items-center gap-2 text-[12.5px] text-fg-2">
        <Switch.Root
          checked={checked}
          onCheckedChange={onChange}
          className="relative h-[18px] w-8 shrink-0 cursor-pointer rounded-full bg-surface-3 transition-colors data-[state=checked]:bg-accent"
        >
          <Switch.Thumb className="block size-3.5 translate-x-0.5 rounded-full bg-fg transition-transform data-[state=checked]:translate-x-[15px] data-[state=checked]:bg-accent-ink" />
        </Switch.Root>
        {label}
      </label>
    </Tip>
  );
}

// Controls for the shared demo campaign. Always labeled Demo: nothing here
// starts work on the lab.
export function ReplayBar() {
  const replay = useReplay();
  const { campaign } = replay;
  if (!campaign) return <div className="h-12 animate-pulse rounded-lg bg-surface" />;
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3 rounded-lg border border-line bg-surface px-3 py-2.5">
      <div className="flex items-center gap-2">
        <Tip
          content={
            <div className="grid gap-1">
              <div className="text-fg">Demo replay. Nothing runs on the lab.</div>
              <div>
                Outcomes and per-phase timings replay recorded runs:{" "}
                {campaign.sourceRuns.map((s) => `${s.model.replace(/:latest$/, "")} (${runDate(s.runId)})`).join(", ")}. Commands, telemetry, and topology are simulated.
              </div>
            </div>
          }
        >
          <span>
            <Tag tone="accent">Demo</Tag>
          </span>
        </Tip>
        <button
          type="button"
          onClick={() => replay.setPlaying(!replay.playing)}
          disabled={replay.frozen}
          aria-label={replay.playing ? "Pause replay" : "Play replay"}
          className="grid size-8 cursor-pointer place-items-center rounded-md bg-fg text-bg transition-colors hover:bg-fg/85 disabled:opacity-40"
        >
          {replay.playing ? <Pause className="size-3.5" strokeWidth={2.25} /> : <Play className="size-3.5 translate-x-px" strokeWidth={2.25} />}
        </button>
        <button type="button" onClick={replay.restart} aria-label="Restart replay" className="grid size-8 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2 hover:text-fg">
          <RotateCcw className="size-3.5" strokeWidth={2} />
        </button>
      </div>

      <div className="flex min-w-[220px] flex-1 items-center gap-3">
        <span className="num w-14 text-right text-[12px] text-fg-2">{clock(replay.t)}</span>
        <Slider.Root
          value={[replay.t]}
          max={campaign.total}
          step={1}
          onValueChange={([value]) => replay.seek(value)}
          disabled={replay.frozen}
          aria-label="Scrub the demo campaign"
          className="relative flex h-5 flex-1 touch-none items-center select-none data-[disabled]:opacity-50"
        >
          <Slider.Track className="relative h-1 grow overflow-hidden rounded-full bg-surface-3">
            <Slider.Range className="absolute h-full rounded-full bg-fg-2" />
          </Slider.Track>
          <Slider.Thumb className="block size-3.5 rounded-full border-2 border-surface bg-fg shadow-[0_0_0_1px_var(--line-strong)]" />
        </Slider.Root>
        <span className="num w-14 text-[12px] text-fg-3">{clock(campaign.total)}</span>
      </div>

      <div className="flex items-center gap-1 rounded-md border border-line p-0.5" role="group" aria-label="Replay speed">
        {SPEEDS.map((speed) => (
          <button
            key={speed}
            type="button"
            aria-pressed={replay.speed === speed}
            onClick={() => replay.setSpeed(speed)}
            className={clsx("num h-6 cursor-pointer rounded-[4px] px-2 text-[11.5px]", replay.speed === speed ? "bg-surface-3 text-fg" : "text-fg-3 hover:text-fg")}
          >
            {speed}×
          </button>
        ))}
      </div>

      <div className="flex items-center gap-4">
        <Toggle label="Failure branch" hint="Replay the campaign with a setup error on attempt 13, so the failed state can be judged." checked={replay.failure} onChange={replay.setFailure} />
        <Toggle label="Frozen" hint="Hold a mid-run moment instead of replaying, to compare a still state with a live one." checked={replay.frozen} onChange={replay.setFrozen} />
      </div>
    </div>
  );
}
