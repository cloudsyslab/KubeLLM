import { PageHeader } from "@/components/ui";

// Views that land after the checkpoint-1 review keep their place in the
// navigation so the information architecture can be judged as a whole.
export function PendingPage({ eyebrow, title, description, items }: { eyebrow: string; title: string; description: string; items: string[] }) {
  return (
    <div className="grid gap-8">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <div className="rounded-lg border border-dashed border-line-strong px-6 py-8">
        <div className="label">Where to go</div>
        <ul className="mt-4 grid gap-2.5 text-[13.5px] text-fg-2">
          {items.map((item) => (
            <li key={item} className="flex gap-3">
              <span className="mt-[9px] size-1 shrink-0 rounded-full bg-fg-3" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
