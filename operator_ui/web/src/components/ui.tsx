import clsx from "clsx";
import { ToggleGroup, Tooltip } from "radix-ui";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: "sm" | "md" }) {
  return (
    <button
      type="button"
      className={clsx(
        "inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-md font-medium whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        size === "sm" ? "h-7 px-2.5 text-[12.5px]" : "h-8 px-3 text-[13px]",
        variant === "primary" && "bg-fg text-bg hover:bg-fg/85",
        variant === "secondary" && "border border-line-strong bg-surface text-fg hover:bg-surface-2",
        variant === "ghost" && "text-fg-2 hover:bg-surface-2 hover:text-fg",
        className,
      )}
      {...props}
    />
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: ReactNode; hint?: string }[];
  label: string;
}) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      aria-label={label}
      onValueChange={(next) => next && onChange(next as T)}
      className="inline-flex h-8 items-center rounded-md border border-line bg-surface p-0.5"
    >
      {options.map((option) => (
        <ToggleGroup.Item
          key={option.value}
          value={option.value}
          title={option.hint}
          className="inline-flex h-full cursor-pointer items-center gap-1.5 rounded-[4px] px-2.5 text-[12.5px] text-fg-3 transition-colors hover:text-fg data-[state=on]:bg-surface-3 data-[state=on]:text-fg"
        >
          {option.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}

export function Tag({ children, tone = "neutral", className }: { children: ReactNode; tone?: "neutral" | "accent" | "warn"; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex h-5 shrink-0 items-center gap-1 rounded-[4px] border px-1.5 whitespace-nowrap font-mono text-[10.5px] font-medium tracking-[0.06em] uppercase",
        tone === "neutral" && "border-line-strong text-fg-3",
        tone === "accent" && "border-accent-line bg-accent-soft text-accent",
        tone === "warn" && "border-warn/40 bg-warn-soft text-warn",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Dot({ color, className }: { color: string; className?: string }) {
  return <span aria-hidden className={clsx("inline-block size-2 shrink-0 rounded-full", className)} style={{ background: color }} />;
}

export function Outcome({ outcome, compact }: { outcome: "pass" | "fail" | "unknown"; compact?: boolean }) {
  const meta = {
    pass: { word: "Pass", dot: "bg-good", text: "text-good" },
    fail: { word: "Fail", dot: "bg-bad", text: "text-bad" },
    unknown: { word: "Unknown", dot: "border border-fg-3 bg-transparent", text: "text-fg-3" },
  }[outcome];
  return (
    <span className={clsx("inline-flex items-center gap-1.5 font-medium", compact ? "text-[12px]" : "text-[12.5px]", meta.text)}>
      <span aria-hidden className={clsx("size-[7px] rounded-full", meta.dot)} />
      {meta.word}
    </span>
  );
}

export function Tip({ content, children, side = "top" }: { content: ReactNode; children: ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side={side}
          sideOffset={6}
          collisionPadding={12}
          className="z-50 max-w-72 rounded-md bg-surface-2 px-3 py-2 text-[12.5px] leading-snug text-fg-2 shadow-pop"
        >
          {content}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export function Panel({
  title,
  caption,
  actions,
  children,
  className,
  flush,
}: {
  title: ReactNode;
  caption?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  flush?: boolean;
}) {
  return (
    <section className={clsx("min-w-0 rounded-lg border border-line bg-surface", className)}>
      <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-[13.5px] leading-5 font-medium">{title}</h2>
          {caption && <p className="mt-0.5 text-[12.5px] text-fg-3">{caption}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </header>
      <div className={clsx(!flush && "p-4")}>{children}</div>
    </section>
  );
}

export function Kpi({ label, value, detail, className }: { label: ReactNode; value: ReactNode; detail?: ReactNode; className?: string }) {
  return (
    <div className={clsx("min-w-0", className)}>
      <div className="label">{label}</div>
      <div className="num mt-1.5 text-[22px] leading-none font-medium tracking-[-0.02em] text-fg">{value}</div>
      {detail && <div className="mt-1.5 truncate text-[12.5px] text-fg-3">{detail}</div>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <div className="label mb-2">{eyebrow}</div>}
        <h1 className="text-[28px] leading-[1.1] font-medium tracking-[-0.03em]">{title}</h1>
        {description && <p className="mt-2 text-[14px] leading-relaxed text-fg-2">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
