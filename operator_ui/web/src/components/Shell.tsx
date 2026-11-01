import clsx from "clsx";
import {
  ChartColumn,
  Columns2,
  Cpu,
  Database,
  Layers,
  LayoutGrid,
  Menu,
  Moon,
  Network,
  Rocket,
  ShieldCheck,
  SquareTerminal,
  Sun,
  X,
  type LucideIcon,
} from "lucide-react";
import { Dialog } from "radix-ui";
import { useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router";
import { api } from "@/api/client";
import { useTheme } from "@/lib/theme";
import { Tip } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Evaluate",
    items: [
      { to: "/", label: "Models", icon: ChartColumn, end: true },
      { to: "/runs", label: "Runs", icon: Layers },
      { to: "/compare", label: "Compare", icon: Columns2 },
    ],
  },
  {
    group: "Operate",
    items: [
      { to: "/execution", label: "Execution", icon: SquareTerminal },
      { to: "/launch", label: "New campaign", icon: Rocket },
      { to: "/environment", label: "Environment", icon: ShieldCheck },
    ],
  },
  {
    group: "Lab",
    items: [
      { to: "/lab", label: "Resources", icon: Cpu },
      { to: "/lab/topology", label: "Topology", icon: Network },
    ],
  },
  {
    group: "Design review",
    items: [{ to: "/options", label: "Options room", icon: LayoutGrid }],
  },
];

export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="none">
      <path d="M12 2.5 20.2 7.25v9.5L12 21.5l-8.2-4.75v-9.5L12 2.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M9 8v8M9 12l5.5-4M11.2 10.5 15 16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <Mark className="size-[22px] text-fg" />
      <div className="leading-none">
        <div className="text-[14.5px] font-semibold tracking-[-0.01em]">KubeLLM</div>
      </div>
      <span className="label ml-0.5 !text-[10px]">Operator</span>
    </div>
  );
}

function Lane() {
  return (
    <Tip side="right" content="Operational controls act only on this explicitly selected private lane. Other lab profiles are visible read-only.">
      <div className="mx-3 rounded-md border border-line px-3 py-2.5">
        <div className="label !text-[10px]">Selected lane</div>
        <div className="mt-1.5 flex items-center gap-2 text-[13px]">
          <span className="size-1.5 rounded-full bg-accent" aria-hidden />
          <span className="ident text-fg">minh-lane</span>
          <span className="ml-auto text-[11.5px] text-fg-3">private</span>
        </div>
      </div>
    </Tip>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="grid gap-5 px-3">
      {NAV.map((section) => (
        <div key={section.group}>
          <div className="label mb-1.5 px-2 !text-[10px]">{section.group}</div>
          <ul className="grid gap-px">
            {section.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end ?? item.to === "/lab"}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    clsx(
                      "group flex h-8 items-center gap-2.5 rounded-md px-2 text-[13.5px] transition-colors",
                      isActive ? "bg-surface-2 text-fg" : "text-fg-2 hover:bg-surface-2/60 hover:text-fg",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon className={clsx("size-[15px]", isActive ? "text-accent" : "text-fg-3 group-hover:text-fg-2")} strokeWidth={1.75} />
                      {item.label}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function Footer() {
  const [theme, toggle] = useTheme();
  return (
    <div className="flex items-center gap-2 border-t border-line px-4 py-3">
      <Tip side="right" content={api.source.mode === "fixture" ? "Reading the committed snapshot of recorded exports in data/. Live views are simulated." : "Reading the operator backend."}>
        <div className="flex min-w-0 items-center gap-2 text-[12px] text-fg-3">
          <Database className="size-3.5 shrink-0" strokeWidth={1.75} />
          <span className="truncate">{api.source.label}</span>
        </div>
      </Tip>
      <button
        type="button"
        onClick={toggle}
        aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        className="ml-auto grid size-7 cursor-pointer place-items-center rounded-md text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg"
      >
        {theme === "dark" ? <Sun className="size-[15px]" strokeWidth={1.75} /> : <Moon className="size-[15px]" strokeWidth={1.75} />}
      </button>
    </div>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 shrink-0 items-center px-5">
        <Brand />
      </div>
      <div className="flex-1 overflow-y-auto pb-6">
        <Lane />
        <div className="mt-5">
          <NavLinks onNavigate={onNavigate} />
        </div>
      </div>
      <Footer />
    </div>
  );
}

const CRUMBS: Record<string, [string, string]> = {
  "/": ["Evaluate", "Models"],
  "/runs": ["Evaluate", "Runs"],
  "/compare": ["Evaluate", "Compare"],
  "/execution": ["Operate", "Execution"],
  "/launch": ["Operate", "New campaign"],
  "/environment": ["Operate", "Environment"],
  "/lab": ["Lab", "Resources"],
  "/lab/topology": ["Lab", "Topology"],
  "/options": ["Design review", "Options room"],
};

export function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const crumbs = CRUMBS[pathname] ?? (pathname.startsWith("/models/") ? ["Evaluate", "Models"] : pathname.startsWith("/runs/") ? ["Evaluate", "Runs"] : ["KubeLLM", ""]);

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[236px_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh border-r border-line lg:block">
        <SidebarBody />
      </aside>

      <Dialog.Root open={open} onOpenChange={setOpen}>
        <header className="sticky top-0 z-30 flex h-12 items-center gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur-md lg:hidden">
          <Dialog.Trigger asChild>
            <button type="button" aria-label="Open navigation" className="grid size-8 cursor-pointer place-items-center rounded-md text-fg-2 hover:bg-surface-2">
              <Menu className="size-[18px]" strokeWidth={1.75} />
            </button>
          </Dialog.Trigger>
          <Brand />
        </header>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 lg:hidden" />
          <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-[272px] border-r border-line bg-bg lg:hidden" aria-describedby={undefined}>
            <Dialog.Title className="sr-only">Navigation</Dialog.Title>
            <Dialog.Close asChild>
              <button type="button" aria-label="Close navigation" className="absolute top-3 right-3 grid size-8 cursor-pointer place-items-center rounded-md text-fg-3 hover:bg-surface-2">
                <X className="size-[17px]" strokeWidth={1.75} />
              </button>
            </Dialog.Close>
            <SidebarBody onNavigate={() => setOpen(false)} />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <div className="min-w-0">
        <div className="sticky top-0 z-20 hidden h-14 items-center border-b border-line bg-bg/85 px-8 backdrop-blur-md lg:flex">
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px]">
            <span className="text-fg-3">{crumbs[0]}</span>
            <span className="text-fg-3/60">/</span>
            <span className="text-fg">{crumbs[1]}</span>
          </nav>
        </div>
        <main className="mx-auto w-full max-w-[1440px] px-4 pt-6 pb-16 sm:px-6 lg:px-8 lg:pt-8">{children}</main>
      </div>
    </div>
  );
}
