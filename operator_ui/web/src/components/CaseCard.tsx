import { Check } from "lucide-react";
import { HoverCard } from "radix-ui";
import type { ReactNode } from "react";
import data from "@/data/cases.json";
import { caseFamily, humanize } from "@/lib/cases";

interface CaseInfo {
  title: string;
  symptom: string;
  setup: string[];
  checks: string[];
  solution: string[];
  ground_truth: string;
}

const CASES = (data as unknown as { cases: Record<string, CaseInfo> }).cases;

export const caseInfo = (id: string): CaseInfo | undefined => CASES[id];

const clip = (text: string, max = 220) => (text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text);

// Readme titles are Title Case ("App Server Bound To Loopback Address"); the UI
// speaks in sentence case. Acronyms and identifiers keep their capitals.
const sentence = (title: string) =>
  title
    .split(" ")
    .map((word, i) => (i === 0 || /[A-Z].*[A-Z]|\d|_/.test(word) ? word : word.toLowerCase()))
    .join(" ");

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1">
      <div className="label !text-[10px]">{label}</div>
      <div className="text-[12.5px] leading-relaxed text-fg-2">{children}</div>
    </div>
  );
}

function Card({ trigger, children, side = "right" }: { trigger: ReactNode; children: ReactNode; side?: "right" | "bottom" | "top" | "left" }) {
  return (
    <HoverCard.Root openDelay={250} closeDelay={80}>
      <HoverCard.Trigger asChild>{trigger}</HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content
          side={side}
          align="start"
          sideOffset={8}
          collisionPadding={12}
          className="z-50 grid w-[min(360px,calc(100vw-24px))] gap-3 rounded-lg bg-surface-2 p-4 shadow-pop"
        >
          {children}
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}

// Explains one benchmark case: what the agents are told, what is actually
// broken, what Ground Truth checks, and the documented fix. Operator-facing.
export function VariantCard({ id, children, side }: { id: string; children: ReactNode; side?: "right" | "bottom" | "top" | "left" }) {
  const info = caseInfo(id);
  const { family, variant } = caseFamily(id);
  return (
    <Card trigger={children} side={side}>
      <div>
        <div className="label !text-[10px]">
          {humanize(family)} · {variant === "base" ? "base case" : "variant"}
        </div>
        <div className="mt-1 text-[14px] leading-snug font-medium text-fg">{info?.title ? sentence(info.title) : humanize(id)}</div>
        <div className="ident mt-0.5 text-[11.5px] text-fg-3">{id}</div>
      </div>
      {info ? (
        <>
          <Section label="Symptom given to the agents">“{clip(info.symptom)}”</Section>
          {info.setup.length > 0 && (
            <Section label="What is broken">
              <ul className="grid gap-1">
                {info.setup.slice(0, 3).map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="mt-[8px] size-1 shrink-0 rounded-full bg-fg-3" aria-hidden />
                    {clip(item, 160)}
                  </li>
                ))}
              </ul>
            </Section>
          )}
          <Section label="Ground Truth passes when">
            <ul className="grid gap-1">
              {info.checks.map((check) => (
                <li key={check} className="flex gap-2">
                  <Check className="mt-[3px] size-3 shrink-0 text-fg-3" strokeWidth={2} />
                  {check}
                </li>
              ))}
            </ul>
          </Section>
          {info.solution.length > 0 && <Section label="Expected fix">{clip(info.solution[0], 200)}</Section>}
        </>
      ) : (
        <p className="text-[12.5px] text-fg-3">No scenario definition was found for this case.</p>
      )}
    </Card>
  );
}

// Explains a scenario family and how its variants differ, using each
// variant's own symptom.
export function FamilyCard({ family, ids, children, side }: { family: string; ids: string[]; children: ReactNode; side?: "right" | "bottom" | "top" | "left" }) {
  const base = ids.find((id) => caseFamily(id).variant === "base") ?? ids[0];
  const baseInfo = caseInfo(base);
  return (
    <Card trigger={children} side={side}>
      <div>
        <div className="label !text-[10px]">Scenario · {ids.length} {ids.length === 1 ? "case" : "cases"}</div>
        <div className="mt-1 text-[14px] leading-snug font-medium text-fg">{humanize(family)}</div>
        {baseInfo && <div className="mt-1 text-[12.5px] leading-relaxed text-fg-2">“{clip(baseInfo.symptom, 160)}”</div>}
      </div>
      <Section label="How the variants differ">
        <ul className="grid gap-2">
          {ids.map((id) => {
            const info = caseInfo(id);
            return (
              <li key={id} className="grid gap-0.5">
                <span className="ident text-[11.5px] text-fg">{caseFamily(id).variant}</span>
                <span className="text-fg-2">{info ? (info.title ? sentence(info.title) : clip(info.symptom, 150)) : "No definition found."}</span>
              </li>
            );
          })}
        </ul>
      </Section>
      <p className="text-[11.5px] text-fg-3">Hover a variant for its broken setup, Ground Truth checks, and fix.</p>
    </Card>
  );
}
