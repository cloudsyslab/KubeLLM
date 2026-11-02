import { CircleX } from "lucide-react";

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="grid gap-4" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div className="h-16 animate-pulse rounded-lg bg-surface" />
      <div className="grid gap-4 xl:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-72 animate-pulse rounded-lg bg-surface" />
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-lg bg-surface" />
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-line bg-surface p-5" role="alert">
      <CircleX className="mt-0.5 size-4 shrink-0 text-bad" strokeWidth={1.75} />
      <div>
        <div className="text-[13.5px] font-medium">Could not load this view</div>
        <p className="mt-1 text-[13px] text-fg-2">{error instanceof Error ? error.message : "Unknown error."}</p>
      </div>
    </div>
  );
}
