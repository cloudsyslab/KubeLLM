import clsx from "clsx";
import { Check, CornerDownLeft, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { Technique } from "@/api/types";
import { caseInfo } from "@/components/CaseCard";
import { displayModel } from "@/components/charts";
import { ModelCardBody } from "@/components/ModelCard";
import { Tag } from "@/components/ui";
import { caseFamily, humanize } from "@/lib/cases";
import { techniqueLabel } from "@/lib/explore";
import { count, duration, usd } from "@/lib/format";
import { LANE, LiveAnnouncer, ScenarioSwitch, StatusWord, countdown, useFreshness } from "../environment/readiness";
import {
  BASE_CASES,
  CATALOG,
  FAMILIES,
  MAX_REPETITIONS,
  ModelChip,
  NotInstalled,
  PreflightButton,
  ReviewDialog,
  TECHNIQUES,
  attemptAt,
  attemptLabel,
  effectiveModels,
  estimate,
  plannedCount,
  requestBody,
  runnerCommand,
  toggle,
  useHistory,
  validModelId,
  validate,
  type History,
  type Plan,
} from "./plan";

type Field = "cases" | "models" | "techniques" | "repetitions";
const FIELDS: Field[] = ["cases", "models", "techniques", "repetitions"];

interface Item {
  key: string;
  kind: "family" | "case" | "model" | "custom" | "technique" | "reps" | "action";
  label: string;
  sub?: string;
  selected: boolean;
  indeterminate?: boolean;
  apply: () => void;
}

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
const MOD = isMac ? "⌘" : "Ctrl";

function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-[4px] border border-line-strong bg-surface-2 px-1 font-mono text-[10.5px] text-fg-2">{children}</kbd>;
}

function Token({ field, active, onFocus, children, label }: { field: Field; active: boolean; onFocus: (field: Field) => void; children: ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={() => onFocus(field)}
      aria-label={`${label}. Edit ${field}`}
      aria-pressed={active}
      className={clsx(
        "inline-flex max-w-full min-w-0 cursor-pointer items-center gap-1.5 rounded-md border px-2 py-0.5 text-left text-[14px] transition-colors",
        active ? "border-accent bg-accent-soft text-fg" : "border-line-strong bg-surface-2 text-fg hover:border-fg-3",
      )}
    >
      {children}
    </button>
  );
}

function casesPhrase(cases: string[]) {
  if (cases.length === CATALOG.length) return `all ${CATALOG.length} cases`;
  if (cases.length === BASE_CASES.length && BASE_CASES.every((c) => cases.includes(c))) return `${BASE_CASES.length} base cases`;
  if (!cases.length) return "no cases";
  const families = FAMILIES.filter((f) => f.cases.some((c) => cases.includes(c.id)));
  if (families.length === 1) return `${humanize(families[0].family)} · ${cases.length}`;
  return `${cases.length} cases in ${families.length} scenarios`;
}

function Inspector({ item, history, plan }: { item?: Item; history?: History; plan: Plan }) {
  if (!item) return <p className="text-[12.5px] text-fg-3">Move through the list to see what each entry is.</p>;
  if (item.kind === "case") {
    const info = caseInfo(item.key);
    return (
      <div className="grid gap-2.5">
        <div>
          <div className="label !text-[10px]">{humanize(caseFamily(item.key).family)}</div>
          <div className="ident mt-0.5 text-[13px] text-fg">{item.key}</div>
        </div>
        {info && <p className="text-[12.5px] leading-relaxed text-fg-2">“{info.symptom}”</p>}
        {info && (
          <div>
            <div className="label mb-1 !text-[10px]">Ground Truth passes when</div>
            <ul className="grid gap-0.5 text-[12px] text-fg-2">
              {info.checks.map((c) => (
                <li key={c} className="flex gap-1.5">
                  <Check className="mt-[3px] size-3 shrink-0 text-fg-3" strokeWidth={2} />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
        {history && plan.models.length > 0 && (
          <div>
            <div className="label mb-1 !text-[10px]">Recorded history</div>
            <ul className="grid gap-0.5 text-[12px]">
              {plan.models.map((m) => {
                const cell = history.cell(m, item.key, plan.techniques);
                return (
                  <li key={m} className="flex items-center justify-between gap-2">
                    <ModelChip id={m} className="text-fg-2" />
                    <span className="num text-fg-3">{cell.known ? `${cell.passed}/${cell.known} passed` : cell.attempts ? `${cell.attempts} unknown` : "none"}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    );
  }
  if (item.kind === "family") {
    const family = FAMILIES.find((f) => f.family === item.key);
    return (
      <div className="grid gap-2">
        <div className="label !text-[10px]">Scenario · {family?.cases.length} cases</div>
        <div className="text-[13px] font-medium text-fg">{humanize(item.key)}</div>
        <ul className="grid gap-1.5 text-[12px]">
          {family?.cases.map((c) => (
            <li key={c.id} className="grid gap-0.5">
              <span className="ident text-fg">{c.variant}</span>
              <span className="text-fg-3">{caseInfo(c.id)?.symptom.slice(0, 110)}…</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (item.kind === "model") {
    const stats = history?.models.find((m) => m.id === item.key);
    return stats?.config ? <ModelCardBody config={stats.config} /> : <p className="text-[12.5px] text-fg-3">No recorded history for this model.</p>;
  }
  if (item.kind === "custom") return <p className="text-[12.5px] text-fg-2">The runner receives this ID verbatim as --debug-model. It has no recorded history, so estimates borrow broader medians.</p>;
  if (item.kind === "technique") {
    const t = TECHNIQUES.find((x) => x.id === item.key)!;
    return (
      <div className="grid gap-2">
        <div className="ident text-[13px] text-fg">{t.id}</div>
        <p className="text-[12.5px] leading-relaxed text-fg-2">{t.blurb}</p>
        {history && (
          <ul className="grid gap-0.5 text-[12px]">
            {effectiveModels(plan)
              .filter((m): m is string => m !== null)
              .map((m) => {
                const combo = history.combo(m, t.id);
                return (
                  <li key={m} className="flex items-center justify-between gap-2">
                    <ModelChip id={m} className="text-fg-2" />
                    <span className={clsx("num", combo.basis === "recorded" ? "text-fg-3" : "text-warn")}>{combo.basis === "recorded" ? `${combo.n} attempts recorded` : "no recorded runs"}</span>
                  </li>
                );
              })}
          </ul>
        )}
      </div>
    );
  }
  return <p className="text-[12.5px] text-fg-2">Each repetition reruns every case with every model and technique. Up to {MAX_REPETITIONS}; a campaign is capped at 5,000 attempts.</p>;
}

function Preview({ plan, history }: { plan: Plan; history?: History }) {
  const [tab, setTab] = useState<"request" | "manifest" | "order">("request");
  const total = plannedCount(plan);
  const body = requestBody(plan);
  const manifest = {
    schema_version: 1,
    campaign_id: "<assigned at launch>",
    status: "running",
    cases: body.cases,
    techniques: body.techniques,
    debug_models: effectiveModels(plan),
    api_model: body.api_model || null,
    verification_model: body.verification_model || null,
    repetitions: body.repetitions,
    planned_attempts: total,
    attempts_completed: 0,
  };
  const est = estimate(plan, history);
  const json = (value: unknown) => JSON.stringify(value, null, 2);
  const [rows, setRows] = useState(40);
  return (
    <div className="flex min-h-0 min-w-0 flex-col rounded-lg border border-line bg-surface">
      <div className="flex flex-wrap items-center gap-1 border-b border-line px-2 py-1.5" role="tablist" aria-label="Plan preview">
        {(
          [
            ["request", "Request"],
            ["manifest", "campaign.json"],
            ["order", `Run order · ${count(total)}`],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={clsx("h-7 cursor-pointer rounded-[4px] px-2.5 font-mono text-[11.5px]", tab === id ? "bg-surface-3 text-fg" : "text-fg-3 hover:text-fg")}
          >
            {label}
          </button>
        ))}
        <span className="ml-auto px-1 text-[11.5px] text-fg-3">{tab === "request" ? "Exact body" : tab === "manifest" ? "Fields as worker.py writes them" : "worker labels"}</span>
      </div>
      <div className="max-h-[420px] min-h-[260px] overflow-auto px-4 py-3" role="tabpanel">
        {tab === "request" && (
          <>
            <pre className="font-mono text-[11.5px] leading-[1.6] text-fg-2">
              <span className="text-fg-3">POST /api/campaign</span>
              {"\n"}
              {json(body)}
            </pre>
            <pre className="mt-3 border-t border-line pt-3 font-mono text-[11.5px] leading-[1.6] text-fg-3">
              <span className="text-fg-3"># attempt 0001, as the worker invokes the runner (paths shortened)</span>
              {"\n"}
              <span className="text-fg-2">{runnerCommand(plan).join(" \\\n")}</span>
            </pre>
          </>
        )}
        {tab === "manifest" && <pre className="font-mono text-[11.5px] leading-[1.6] text-fg-2">{json(manifest)}</pre>}
        {tab === "order" && (
          <ol className="grid font-mono text-[11.5px] leading-[1.65]">
            {Array.from({ length: Math.min(rows, total) }, (_, i) => attemptAt(plan, i)).map((a) => (
              <li key={a.sequence} className="grid grid-cols-[40px_minmax(0,1fr)] gap-2">
                <span className="num text-fg-3">{String(a.sequence).padStart(4, "0")}</span>
                <span className="truncate text-fg-2">{attemptLabel(a)}</span>
              </li>
            ))}
            {total > rows && (
              <li>
                <button type="button" onClick={() => setRows((r) => r + 400)} className="mt-1 cursor-pointer text-fg-3 hover:text-fg">
                  … {count(total - rows)} more
                </button>
              </li>
            )}
          </ol>
        )}
      </div>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-line px-4 py-2 text-[12px] text-fg-3">
        <span>
          Estimate <span className="num text-fg-2">{est.seconds === null ? "—" : `≈ ${duration(est.seconds)}`}</span>
        </span>
        <span>
          <span className="num text-fg-2">{est.cost === null ? "—" : `≈ ${usd(est.cost)}`}</span> API
        </span>
        <span>from recorded medians{est.inferred ? `; ${est.inferred} pair${est.inferred === 1 ? "" : "s"} without history` : ""}</span>
      </div>
    </div>
  );
}

export default function Composer() {
  const history = useHistory();
  const { fresh, canLaunch } = useFreshness();
  const [plan, setPlan] = useState<Plan>({ cases: BASE_CASES, techniques: ["allStepsAtOnce"], models: ["gpt-6-luna", "gpt-5.6-luna"], repetitions: 3, apiModel: "", verificationModel: "" });
  const [field, setField] = useState<Field>("cases");
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [review, setReview] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const update = (next: Partial<Plan>) => setPlan((p) => ({ ...p, ...next }));
  const errors = validate(plan);
  const total = plannedCount(plan);

  const items: Item[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = (...texts: string[]) => !q || texts.some((t) => t.toLowerCase().replaceAll("_", " ").includes(q.replaceAll("_", " ")));
    if (field === "cases") {
      return FAMILIES.flatMap((f) => {
        const ids = f.cases.map((c) => c.id);
        const familyHit = match(f.family);
        const visible = f.cases.filter((c) => familyHit || match(c.id, caseInfo(c.id)?.symptom ?? ""));
        if (!visible.length) return [];
        const on = ids.filter((id) => plan.cases.includes(id)).length;
        return [
          {
            key: f.family,
            kind: "family" as const,
            label: humanize(f.family),
            sub: `${on}/${ids.length}`,
            selected: on === ids.length,
            indeterminate: on > 0 && on < ids.length,
            apply: () => update({ cases: on === ids.length ? plan.cases.filter((id) => !ids.includes(id)) : [...new Set([...plan.cases, ...ids])] }),
          },
          ...visible.map((c) => ({
            key: c.id,
            kind: "case" as const,
            label: c.variant === "base" ? "base" : c.variant,
            sub: c.id,
            selected: plan.cases.includes(c.id),
            apply: () => update({ cases: toggle(plan.cases, c.id, !plan.cases.includes(c.id)) }),
          })),
        ];
      });
    }
    if (field === "models") {
      const list: Item[] = (history?.models ?? [])
        .filter((m) => match(m.id))
        .map((m) => ({ key: m.id, kind: "model" as const, label: displayModel(m.id), sub: m.config ? `${m.config.known} recorded outcomes` : "", selected: plan.models.includes(m.id), apply: () => update({ models: toggle(plan.models, m.id, !plan.models.includes(m.id)) }) }));
      plan.models
        .filter((id) => !history?.models.some((m) => m.id === id) && match(id))
        .forEach((id) => list.push({ key: id, kind: "custom", label: id, sub: "custom ID", selected: true, apply: () => update({ models: plan.models.filter((m) => m !== id) }) }));
      const typed = query.trim();
      if (typed && validModelId(typed) && !list.some((i) => i.key === typed)) {
        list.push({ key: typed, kind: "custom", label: `Add “${typed}”`, sub: "model ID, verbatim", selected: false, apply: () => (update({ models: toggle(plan.models, typed, true) }), setQuery("")) });
      }
      return list;
    }
    if (field === "techniques") {
      return TECHNIQUES.filter((t) => match(t.id, techniqueLabel(t.id))).map((t) => ({
        key: t.id,
        kind: "technique" as const,
        label: techniqueLabel(t.id),
        sub: t.id,
        selected: plan.techniques.includes(t.id),
        apply: () => update({ techniques: toggle<Technique>(plan.techniques, t.id, !plan.techniques.includes(t.id)) }),
      }));
    }
    const typed = Number.parseInt(query, 10);
    const values = [...new Set([...(Number.isFinite(typed) && typed >= 1 && typed <= MAX_REPETITIONS ? [typed] : []), 1, 3, 5, 10])];
    return values.map((n) => ({ key: String(n), kind: "reps" as const, label: `${n} ${n === 1 ? "repetition" : "repetitions"}`, sub: `${count(plan.cases.length * effectiveModels(plan).length * plan.techniques.length * n)} attempts`, selected: plan.repetitions === n, apply: () => update({ repetitions: n }) }));
  }, [field, query, plan, history]);

  useEffect(() => setHighlight((h) => Math.min(h, Math.max(0, items.length - 1))), [items.length]);
  useEffect(() => {
    document.getElementById(`${listId}-${highlight}`)?.scrollIntoView({ block: "nearest" });
  }, [highlight, listId]);

  const focusField = (next: Field) => {
    setField(next);
    setQuery("");
    setHighlight(0);
    input.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!errors.length) setReview(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(items.length - 1, h + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(0, h - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      items[highlight]?.apply();
    } else if (e.key === "Tab") {
      e.preventDefault();
      const i = FIELDS.indexOf(field);
      focusField(FIELDS[(i + (e.shiftKey ? FIELDS.length - 1 : 1)) % FIELDS.length]);
    } else if (e.key === "Escape") {
      if (query) {
        e.preventDefault();
        setQuery("");
      }
    } else if (e.altKey && e.code === "KeyA") {
      e.preventDefault();
      if (field === "cases") update({ cases: plan.cases.length === CATALOG.length ? [] : CATALOG });
    }
  };

  const active = items[highlight];

  return (
    <div className="grid gap-4">
      <LiveAnnouncer />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12.5px] text-fg-3">
          Compose with the keyboard: <Kbd>Tab</Kbd> next field, <Kbd>↑</Kbd>
          <Kbd>↓</Kbd> move, <Kbd>↵</Kbd> toggle, <Kbd>{MOD}</Kbd>
          <Kbd>↵</Kbd> review.
        </p>
        <ScenarioSwitch />
      </div>

      <div className="rounded-lg border border-line bg-surface">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-2 border-b border-line px-4 py-4 text-[14px] text-fg-3" aria-label="Campaign sentence">
          <span>Run</span>
          <Token field="cases" active={field === "cases"} onFocus={focusField} label={casesPhrase(plan.cases)}>
            {casesPhrase(plan.cases)}
          </Token>
          <span>with</span>
          <Token field="models" active={field === "models"} onFocus={focusField} label={plan.models.map(displayModel).join(", ") || "case default model"}>
            {plan.models.length ? (
              <span className="flex min-w-0 flex-wrap items-center gap-x-2">
                {plan.models.slice(0, 3).map((m) => (
                  <ModelChip key={m} id={m} />
                ))}
                {plan.models.length > 3 && <span className="text-fg-3">+{plan.models.length - 3}</span>}
              </span>
            ) : (
              "case default model"
            )}
          </Token>
          <span>using</span>
          <Token field="techniques" active={field === "techniques"} onFocus={focusField} label={plan.techniques.map(techniqueLabel).join(", ") || "no technique"}>
            {plan.techniques.length ? plan.techniques.map((t) => techniqueLabel(t).toLowerCase()).join(" + ") : "no technique"}
          </Token>
          <span>×</span>
          <Token field="repetitions" active={field === "repetitions"} onFocus={focusField} label={`${plan.repetitions} repetitions`}>
            <span className="num">{plan.repetitions}</span>
          </Token>
          <span className="ml-auto inline-flex items-baseline gap-1.5 pl-2">
            <span className="text-fg-3">=</span>
            <span className="num text-[18px] font-medium text-fg">{count(total)}</span>
            <span className="text-[12.5px]">attempts</span>
          </span>
        </div>

        <div className="grid min-w-0 md:grid-cols-[minmax(0,1fr)_minmax(0,300px)]">
          <div className="min-w-0 border-b border-line md:border-r md:border-b-0">
            <label className="flex h-10 items-center gap-2 border-b border-line px-4 text-fg-3">
              <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
              <span className="sr-only">Filter {field}</span>
              <input
                ref={input}
                role="combobox"
                aria-expanded
                aria-controls={listId}
                aria-activedescendant={active ? `${listId}-${highlight}` : undefined}
                aria-autocomplete="list"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setHighlight(0);
                }}
                onKeyDown={onKeyDown}
                placeholder={field === "models" ? "Filter models or type any model ID" : field === "repetitions" ? "Type a number, 1 to 500" : `Filter ${field}`}
                className="w-full min-w-0 bg-transparent text-[13px] text-fg outline-none placeholder:text-fg-3"
              />
              <span className="label shrink-0 !text-[10px]">{field}</span>
            </label>
            <ul id={listId} role="listbox" aria-multiselectable={field !== "repetitions"} aria-label={`${field} options`} className="max-h-[340px] overflow-y-auto py-1">
              {items.map((item, i) => (
                <li
                  key={`${item.kind}-${item.key}`}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={item.selected}
                  onMouseMove={() => setHighlight(i)}
                  onClick={() => {
                    item.apply();
                    input.current?.focus();
                  }}
                  className={clsx(
                    "flex cursor-pointer items-center gap-2.5 py-1.5 pr-4 text-[13px]",
                    item.kind === "case" ? "pl-10" : "pl-4",
                    i === highlight && "bg-surface-2",
                  )}
                >
                  <span
                    aria-hidden
                    className={clsx(
                      "grid size-3.5 shrink-0 place-items-center rounded-[3px] border",
                      item.selected ? "border-accent bg-accent text-accent-ink" : item.indeterminate ? "border-accent" : "border-line-strong",
                    )}
                  >
                    {item.selected ? <Check className="size-2.5" strokeWidth={3} /> : item.indeterminate ? <span className="h-0.5 w-1.5 rounded bg-accent" /> : null}
                  </span>
                  {item.kind === "model" ? <ModelChip id={item.key} className="text-fg" /> : <span className={clsx("min-w-0 truncate", item.kind === "case" ? "ident text-fg-2" : "text-fg", item.kind === "family" && "font-medium")}>{item.label}</span>}
                  {item.kind === "model" && history?.models.find((m) => m.id === item.key)?.notInstalled && <NotInstalled />}
                  <span className="ml-auto shrink-0 truncate pl-2 text-[11.5px] text-fg-3">{item.kind === "case" ? "" : item.sub}</span>
                  {i === highlight && <CornerDownLeft className="size-3 shrink-0 text-fg-3" strokeWidth={2} aria-hidden />}
                </li>
              ))}
              {!items.length && <li className="px-4 py-6 text-center text-[12.5px] text-fg-3">{field === "models" ? "Not a valid model ID." : "Nothing matches."}</li>}
            </ul>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line px-4 py-2 text-[11.5px] text-fg-3">
              {field === "cases" && (
                <>
                  <button type="button" className="cursor-pointer hover:text-fg" onClick={() => update({ cases: CATALOG })}>
                    All {CATALOG.length} <Kbd>⌥A</Kbd>
                  </button>
                  <button type="button" className="cursor-pointer hover:text-fg" onClick={() => update({ cases: BASE_CASES })}>
                    Base {BASE_CASES.length}
                  </button>
                  <button type="button" className="cursor-pointer hover:text-fg" onClick={() => update({ cases: [] })}>
                    None
                  </button>
                </>
              )}
              {field === "models" && <span>No model selected runs each case's configured default. Up to 20.</span>}
              {field === "techniques" && <span>Each selected technique multiplies the plan.</span>}
              {field === "repetitions" && <span>Type any number up to {MAX_REPETITIONS}.</span>}
            </div>
          </div>
          <div className="min-w-0 px-4 py-3">
            <div className="label mb-2 !text-[10px]">Highlighted</div>
            <Inspector item={active} history={history} plan={plan} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line px-4 py-2.5 text-[12.5px]">
          <span className="flex items-center gap-2">
            <StatusWord fresh={fresh} />
            <span className="num text-fg-3">{fresh.state === "fresh" ? countdown(fresh.left) : fresh.state === "checking" ? `${fresh.active.done.length}/${fresh.active.total}` : ""}</span>
          </span>
          <span className="ident text-fg-3">{LANE.profile}</span>
          {fresh.state !== "fresh" && <PreflightButton fresh={fresh} />}
          <span className="ml-auto flex items-center gap-2">
            {errors[0] && <span className="text-warn">{errors[0]}</span>}
            {!errors.length && !canLaunch && <span className="text-fg-3">Review now; starting needs fresh readiness.</span>}
            <button
              type="button"
              disabled={errors.length > 0}
              onClick={() => setReview(true)}
              className="inline-flex h-8 cursor-pointer items-center gap-2 rounded-md bg-fg px-3 text-[13px] font-medium text-bg hover:bg-fg/85 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Review
              <span className="font-mono text-[11px] opacity-60">
                {MOD}↵
              </span>
            </button>
          </span>
        </div>
      </div>

      <Preview plan={plan} history={history} />
      <p className="flex items-center gap-2 text-[11.5px] text-fg-3">
        <Tag>Exact</Tag> The request body and run order are what this plan sends and runs. Estimates are not.
      </p>
      <ReviewDialog plan={plan} open={review} onOpenChange={setReview} />
    </div>
  );
}
