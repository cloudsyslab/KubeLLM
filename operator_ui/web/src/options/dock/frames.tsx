import clsx from "clsx";
import { ChartColumn, Columns2, Cpu, Database, LayoutGrid, Layers, ListChecks, Menu, Network, Rocket, Search, ShieldCheck, SquareTerminal, Sun, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Mark } from "@/components/Shell";
import { Segmented, Tag } from "@/components/ui";

// Scaled-down mocks of the real shell so each active-work option is judged
// where it lives. Only the indicator inside is interactive.

export type PreviewContext = "page" | "execution" | "idle";

const NAV: { group: string; items: { label: string; icon: LucideIcon }[] }[] = [
  { group: "Evaluate", items: [{ label: "Models", icon: ChartColumn }, { label: "Runs", icon: Layers }, { label: "Compare", icon: Columns2 }] },
  { group: "Operate", items: [{ label: "Execution", icon: SquareTerminal }, { label: "Jobs", icon: ListChecks }, { label: "New campaign", icon: Rocket }, { label: "Environment", icon: ShieldCheck }] },
  { group: "Lab", items: [{ label: "Resources", icon: Cpu }, { label: "Topology", icon: Network }] },
  { group: "Design review", items: [{ label: "Options room", icon: LayoutGrid }] },
];

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <Mark className="size-[18px] text-fg" />
      <span className="text-[13px] font-semibold tracking-[-0.01em]">KubeLLM</span>
      <span className="label !text-[9px]">Operator</span>
    </div>
  );
}

function SidebarMock({ active, slot }: { active: string; slot?: ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div inert className="flex h-12 shrink-0 items-center px-4">
        <Brand />
      </div>
      <div inert className="min-h-0 flex-1 overflow-hidden">
        <div className="mx-2.5 rounded-md border border-line px-2.5 py-2">
          <div className="label !text-[9px]">Selected lane</div>
          <div className="mt-1 flex items-center gap-1.5 text-[12px]">
            <span className="size-1.5 rounded-full bg-accent" aria-hidden />
            <span className="ident">minh-lane</span>
            <span className="ml-auto text-[10.5px] text-fg-3">private</span>
          </div>
        </div>
        <div className="mt-3 grid gap-3 px-2.5">
          {NAV.map((section) => (
            <div key={section.group}>
              <div className="label mb-1 px-1.5 !text-[9px]">{section.group}</div>
              {section.items.map((item) => (
                <div key={item.label} className={clsx("flex h-7 items-center gap-2 rounded-md px-1.5 text-[12.5px]", item.label === active ? "bg-surface-2 text-fg" : "text-fg-2")}>
                  <item.icon className={clsx("size-[14px]", item.label === active ? "text-accent" : "text-fg-3")} strokeWidth={1.75} />
                  {item.label}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      {slot}
      <div inert className="flex items-center gap-2 border-t border-line px-3.5 py-2.5 text-[11px] text-fg-3">
        <Database className="size-3" strokeWidth={1.75} />
        Recorded snapshot
        <Sun className="ml-auto size-3.5" strokeWidth={1.75} />
      </div>
    </div>
  );
}

function PageSkeleton({ title }: { title: string }) {
  return (
    <div inert aria-hidden className="grid content-start gap-4 p-5">
      <div>
        <div className="label !text-[9px]">{title === "Execution" ? "Operate" : "Evaluate"}</div>
        <div className="mt-1 text-[20px] leading-tight font-medium tracking-[-0.02em]">{title}</div>
        <div className="mt-2 h-2 w-3/5 rounded-full bg-surface-2" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-md border border-line p-3">
            <div className="h-1.5 w-1/3 rounded-full bg-surface-3" />
            <div className="mt-2.5 h-3 w-1/2 rounded-full bg-surface-2" />
            <div className="mt-3 grid gap-1.5">
              {[0.82, 0.64, 0.51, 0.38].map((w, j) => (
                <div key={j} className="h-1.5 rounded-full bg-[var(--bar-muted)] opacity-60" style={{ width: `${w * 100 - i * 6 - j * 2}%` }} />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="rounded-md border border-line">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-3 border-b border-line px-3 py-2.5 last:border-b-0">
            <div className="h-1.5 w-24 rounded-full bg-surface-3" />
            <div className="h-1.5 flex-1 rounded-full bg-surface-2" />
            <div className="h-1.5 w-10 rounded-full bg-surface-3" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function MockDesktop({ page, sidebar, topbar, floating, overlay }: { page: string; sidebar?: ReactNode; topbar?: ReactNode; floating?: ReactNode; overlay?: ReactNode }) {
  const crumb = page === "Execution" ? ["Operate", "Execution"] : ["Evaluate", page];
  return (
    <div className="overflow-x-auto rounded-lg border border-line-strong">
      <div className="relative grid h-[560px] min-w-[720px] grid-cols-[236px_minmax(0,1fr)] overflow-hidden bg-bg">
        <aside className="min-h-0 border-r border-line">
          <SidebarMock active={page} slot={sidebar} />
        </aside>
        <div className="flex min-w-0 flex-col">
          <div className="flex h-12 shrink-0 items-center border-b border-line px-5">
            <div inert className="flex items-center gap-2 text-[12.5px]">
              <span className="text-fg-3">{crumb[0]}</span>
              <span className="text-fg-3/60">/</span>
              <span className="text-fg">{crumb[1]}</span>
            </div>
            <div className="ml-auto flex items-center gap-2">
              {topbar}
              <span inert className="inline-flex h-8 w-36 items-center gap-2 rounded-md border border-line px-2.5 text-[12px] text-fg-3">
                <Search className="size-3.5" strokeWidth={1.75} /> Search
              </span>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <PageSkeleton title={page} />
          </div>
        </div>
        {floating}
        {overlay}
      </div>
    </div>
  );
}

export function MockPhone({ page, headerRight, sheet, floating }: { page: string; headerRight?: ReactNode; sheet?: ReactNode; floating?: ReactNode }) {
  return (
    <div className="relative mx-auto h-[600px] w-full max-w-[320px] overflow-hidden rounded-lg border border-line-strong bg-bg">
      <div className="flex h-11 items-center gap-2.5 border-b border-line px-3">
        <span inert className="grid size-7 place-items-center rounded-md text-fg-2">
          <Menu className="size-4" strokeWidth={1.75} />
        </span>
        <span inert>
          <Brand />
        </span>
        <div className="ml-auto flex items-center gap-1">
          {headerRight}
          <span inert className="grid size-7 place-items-center rounded-md text-fg-2">
            <Search className="size-4" strokeWidth={1.75} />
          </span>
        </div>
      </div>
      <div className="[&_.grid-cols-3]:grid-cols-1">
        <PageSkeleton title={page} />
      </div>
      {floating}
      {sheet && (
        <>
          <div aria-hidden className="absolute inset-0 bg-black/50" />
          <div className="absolute inset-y-0 left-0 w-[272px] max-w-[85%] border-r border-line bg-bg">
            <SidebarMock active={page} slot={sheet} />
          </div>
        </>
      )}
    </div>
  );
}

export function PreviewBar({ value, onChange, note }: { value: PreviewContext; onChange: (next: PreviewContext) => void; note: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <Segmented
        label="Preview context"
        value={value}
        onChange={onChange}
        options={[
          { value: "page", label: "Any page" },
          { value: "execution", label: "On Execution" },
          { value: "idle", label: "Idle" },
        ]}
      />
      <Tag tone="accent">Demo</Tag>
      <p className="min-w-0 basis-full text-[12.5px] text-fg-3 md:basis-0 md:flex-1">{note}</p>
    </div>
  );
}

export function Frames({ desktop, phone, desktopCaption, phoneCaption }: { desktop: ReactNode; phone: ReactNode; desktopCaption: string; phoneCaption: string }) {
  return (
    <div className="grid gap-5 min-[1360px]:grid-cols-[minmax(0,1fr)_320px]">
      <figure className="grid min-w-0 gap-2">
        {desktop}
        <figcaption className="text-[12px] text-fg-3">{desktopCaption}</figcaption>
      </figure>
      <figure className="grid min-w-0 content-start gap-2">
        {phone}
        <figcaption className="text-center text-[12px] text-fg-3">{phoneCaption}</figcaption>
      </figure>
    </div>
  );
}
