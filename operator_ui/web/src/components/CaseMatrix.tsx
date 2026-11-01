import clsx from "clsx";
import { useState } from "react";
import { useNavigate } from "react-router";
import { groupCases, humanize } from "@/lib/cases";
import { techniqueLabel, type CaseTally, type ModelConfig } from "@/lib/explore";
import { duration, pct } from "@/lib/format";
import { displayModel, mixedTechniques } from "./charts";
import { Dot, Tip } from "./ui";

const fill = (share: number) => `color-mix(in oklab, var(--good) ${Math.round(16 + share * 64)}%, var(--track))`;

function cellLook(tally: CaseTally | undefined) {
  if (!tally || tally.known === 0) return { className: "hatch text-fg-3", style: {} };
  const share = tally.passed / tally.known;
  if (share === 0) return { className: "text-bad", style: { background: "var(--bad-soft)" } };
  return { className: share > 0.55 ? "font-medium" : "text-fg", style: { background: fill(share), color: share > 0.55 ? "var(--bg)" : undefined } };
}

const middle = (values: number[]) => (values.length ? [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)] : null);

function CellTip({ config, tally, id }: { config: ModelConfig; tally?: CaseTally; id: string }) {
  return (
    <div className="grid gap-1">
      <div className="ident text-fg">{config.debug}</div>
      <div className="ident text-fg-2">{id}</div>
      {tally ? (
        <>
          <div>
            <span className="num font-medium text-fg">{tally.passed}</span> of <span className="num">{tally.known}</span> known attempts passed Ground Truth
          </div>
          {tally.unknown > 0 && <div className="text-warn">{tally.unknown} with unknown outcome</div>}
          <div className="text-fg-3">Median {duration(middle(tally.durations))} per attempt</div>
        </>
      ) : (
        <div className="text-fg-3">Not attempted in this configuration.</div>
      )}
    </div>
  );
}

// Cases x models, Braintrust-style: cases are rows, models are columns in rank
// order. Each cell counts Ground Truth passes across that model's runs.
export function CaseMatrix({ configs, cases }: { configs: ModelConfig[]; cases: string[] }) {
  const families = groupCases(cases);
  const navigate = useNavigate();
  const showTechnique = mixedTechniques(configs);
  const [focus, setFocus] = useState<{ row: string | null; col: string | null }>({ row: null, col: null });
  const caseShare = (id: string) => {
    const known = configs.reduce((sum, c) => sum + (c.perCase.get(id)?.known ?? 0), 0);
    const passed = configs.reduce((sum, c) => sum + (c.perCase.get(id)?.passed ?? 0), 0);
    return known ? passed / known : null;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] table-fixed border-separate border-spacing-0 text-[12.5px] md:min-w-[820px]" onMouseLeave={() => setFocus({ row: null, col: null })}>
        <thead>
          <tr className="[&>th]:border-b [&>th]:border-line [&>th]:pb-2.5 [&>th]:align-bottom">
            <th scope="col" className="label hidden w-[148px] pl-4 text-left !text-[10.5px] font-medium md:table-cell">Scenario</th>
            <th scope="col" className="label sticky left-0 z-10 w-[150px] bg-surface pl-4 text-left !text-[10.5px] font-medium md:static md:pl-0">
              <span className="md:hidden">Case</span>
              <span className="hidden md:inline">Variant</span>
            </th>
            {configs.map((config) => (
              <th key={config.key} scope="col" className="px-1 text-left font-normal">
                <button
                  type="button"
                  onClick={() => navigate(`/models/${config.slug}`)}
                  onMouseEnter={() => setFocus({ row: null, col: config.key })}
                  className={clsx("flex h-[72px] w-full cursor-pointer flex-col justify-between rounded px-1.5 py-1.5 text-left transition-colors hover:bg-surface-2", focus.col === config.key && "bg-surface-2")}
                >
                  <span className="flex items-start gap-1.5">
                    <Dot color={config.color} className="mt-[5px]" />
                    <span className="ident text-[11.5px] leading-tight [overflow-wrap:anywhere] text-fg">
                      {displayModel(config.debug)}
                      {(showTechnique || config.source !== "canonical") && (
                        <span className="block text-[10px] text-fg-3">
                          {[showTechnique ? techniqueLabel(config.technique).toLowerCase() : null, config.source !== "canonical" ? config.source : null].filter(Boolean).join(" · ")}
                        </span>
                      )}
                    </span>
                  </span>
                  <span className="num pl-3.5 text-[11px] text-fg-3">{pct(config.rate, 0)}</span>
                </button>
              </th>
            ))}
            <th scope="col" className="label w-[112px] pr-4 text-right !text-[10.5px] font-medium">All models</th>
          </tr>
        </thead>
        {families.map((family) => (
          <tbody key={family.family} className="[&>tr:first-child>*]:pt-2 [&>tr:last-child>*]:border-b [&>tr:last-child>*]:border-line [&>tr:last-child>*]:pb-2">
            {family.cases.map((item, index) => {
              const share = caseShare(item.id);
              const rowLit = focus.row === item.id;
              return (
                <tr key={item.id} className={clsx("transition-colors", rowLit && "bg-surface-2/60")}>
                  <td className="hidden py-[3px] pl-4 align-middle md:table-cell">
                    {index === 0 && <span className="text-[12.5px] text-fg-2">{humanize(family.family)}</span>}
                  </td>
                  <td className="sticky left-0 z-10 bg-surface py-[3px] pl-4 align-middle md:static md:bg-transparent md:pl-0">
                    {index === 0 && <span className="block truncate text-[11.5px] text-fg-3 md:hidden">{humanize(family.family)}</span>}
                    <span className={clsx("ident block truncate text-[12px]", rowLit ? "text-fg" : "text-fg-2")} title={item.id}>
                      {item.variant}
                    </span>
                  </td>
                  {configs.map((config) => {
                    const tally = config.perCase.get(item.id);
                    const look = cellLook(tally);
                    const dim = (focus.row !== null || focus.col !== null) && !(focus.row === item.id || focus.col === config.key);
                    return (
                      <td key={config.key} className="px-1 py-[3px]">
                        <Tip content={<CellTip config={config} tally={tally} id={item.id} />}>
                          <button
                            type="button"
                            aria-label={`${config.debug}, ${item.id}: ${tally ? `${tally.passed} of ${tally.known} passed` : "not attempted"}`}
                            onMouseEnter={() => setFocus({ row: item.id, col: config.key })}
                            onFocus={() => setFocus({ row: item.id, col: config.key })}
                            onClick={() => navigate(`/models/${config.slug}?case=${item.id}`)}
                            className={clsx(
                              "num flex h-[24px] w-full cursor-pointer items-center justify-center rounded-[3px] text-[11.5px] transition-[opacity,box-shadow] duration-100",
                              look.className,
                              dim && "opacity-50",
                              focus.row === item.id && focus.col === config.key && "ring-2 ring-accent ring-offset-1 ring-offset-surface",
                            )}
                            style={look.style}
                          >
                            {tally && tally.known > 0 ? (
                              <>
                                {tally.passed}
                                <span className="opacity-60">/{tally.known}</span>
                              </>
                            ) : (
                              ""
                            )}
                          </button>
                        </Tip>
                      </td>
                    );
                  })}
                  <td className="py-[3px] pr-4 pl-3">
                    <div className="flex items-center justify-end gap-2">
                      <span className="relative h-1 w-12 overflow-hidden rounded-full bg-track">
                        {share !== null && <span className={clsx("absolute inset-y-0 left-0 rounded-full", share < 0.35 ? "bg-bad" : "bg-fg-3")} style={{ width: `${share * 100}%` }} />}
                      </span>
                      <span className={clsx("num w-9 text-right text-[12px]", share !== null && share < 0.35 ? "text-bad" : "text-fg-2")}>{pct(share, 0)}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        ))}
      </table>
    </div>
  );
}

export function MatrixLegend({ runs }: { runs: number }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-fg-3">
      <span className="flex items-center gap-1.5">
        <span className="size-3 rounded-[2px]" style={{ background: "var(--bad-soft)" }} />
        None passed
      </span>
      <span className="flex items-center gap-1">
        {[0.2, 0.4, 0.6, 0.8, 1].map((share) => (
          <span key={share} className="size-3 rounded-[2px]" style={{ background: fill(share) }} />
        ))}
        <span className="ml-1">Passes of {runs} runs</span>
      </span>
      <span className="flex items-center gap-1.5">
        <span className="hatch size-3 rounded-[2px] border border-line" />
        Unknown
      </span>
    </div>
  );
}
