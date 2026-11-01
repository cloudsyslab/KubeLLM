import clsx from "clsx";
import { ArrowUpRight, Check, Copy, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { Tip } from "@/components/ui";
import { recommended, useOptionChoice, writeChoice } from "./choice";
import { SURFACES, type SurfaceDef } from "./registry";

function Row({ def }: { def: SurfaceDef }) {
  const [picked, choose] = useOptionChoice(def.id);
  const rec = recommended(def.id);
  return (
    <li className="grid gap-3 px-4 py-3.5 lg:grid-cols-[260px_minmax(0,1fr)_auto] lg:items-center">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[14px] font-medium">{def.label}</span>
          {picked.id !== rec.id && <span className="label !text-[9.5px] !text-accent">Changed</span>}
        </div>
        <p className="mt-0.5 text-[12.5px] text-fg-3">{def.question}</p>
      </div>
      <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={`${def.label} option`}>
        {def.options.map((option) => {
          const on = picked.id === option.id;
          return (
            <Tip key={option.id} content={<div className="grid gap-1"><div className="text-fg">{option.name}</div><div>{option.idea}</div></div>}>
              <button
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => choose(option.id)}
                className={clsx(
                  "inline-flex h-8 cursor-pointer items-center gap-2 rounded-md border px-2.5 text-[12.5px] transition-colors",
                  on ? "border-accent-line bg-accent-soft text-fg" : "border-line text-fg-2 hover:border-line-strong hover:text-fg",
                )}
              >
                <span className={clsx("grid size-[18px] place-items-center rounded-[4px] font-mono text-[11px]", on ? "bg-accent text-accent-ink" : "bg-surface-3 text-fg-3")}>{option.letter}</span>
                {option.name}
                {option.recommended && <span className="size-1.5 rounded-full bg-accent" aria-label="Recommended" />}
              </button>
            </Tip>
          );
        })}
      </div>
      <Link to={`/options?surface=${def.id}&option=${picked.id}`} className="inline-flex items-center gap-1 justify-self-start text-[12.5px] text-fg-3 hover:text-fg lg:justify-self-end">
        Compare <ArrowUpRight className="size-3.5" strokeWidth={1.75} />
      </Link>
    </li>
  );
}

function summaryText(): string {
  const lines = SURFACES.map((def) => {
    let id: string | null = null;
    try {
      id = localStorage.getItem(`kubellm-option-${def.id}`);
    } catch {
      id = null;
    }
    const option = def.options.find((o) => o.id === id) ?? recommended(def.id);
    return `- ${def.label}: ${option.letter} · ${option.name}${option.recommended ? " (recommended)" : ""}`;
  });
  return ["KubeLLM operator option picks", ...lines].join("\n");
}

// One place to consolidate: every surface, its options, and the current pick.
export function PickSheet() {
  const [copied, setCopied] = useState(false);
  const groups = [...new Set(SURFACES.map((s) => s.group))];
  const total = SURFACES.reduce((sum, s) => sum + s.options.length, 0);

  const copy = async () => {
    const text = summaryText();
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface px-4 py-3">
        <p className="text-[13px] text-fg-2">
          Pick one option per surface; the dot marks Claude's recommendation. Picks apply to each page immediately. {total} options in all.
        </p>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => SURFACES.forEach((def) => writeChoice(def.id, null))}
            className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md px-2.5 text-[12.5px] text-fg-3 hover:bg-surface-2 hover:text-fg"
          >
            <RotateCcw className="size-3.5" strokeWidth={1.75} /> Reset to recommended
          </button>
          <button type="button" onClick={copy} className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md bg-fg px-3 text-[12.5px] font-medium text-bg hover:bg-fg/85">
            {copied ? <Check className="size-3.5" strokeWidth={2.25} /> : <Copy className="size-3.5" strokeWidth={2} />}
            {copied ? "Copied" : "Copy my picks"}
          </button>
        </div>
      </div>
      {groups.map((group) => (
        <section key={group} className="overflow-hidden rounded-lg border border-line bg-surface">
          <header className="border-b border-line px-4 py-2.5">
            <h2 className="label !text-[10.5px]">{group}</h2>
          </header>
          <ul className="divide-y divide-line">
            {SURFACES.filter((s) => s.group === group).map((def) => (
              <Row key={def.id} def={def} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
