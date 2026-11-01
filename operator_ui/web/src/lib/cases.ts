// Scenario families group the 27 broken-cluster cases by the fault they share.
// Longest prefixes come first so readiness_missing_dependency is not filed under
// readiness_failure.
const FAMILIES = [
  "readiness_missing_dependency",
  "selector_env_variable",
  "environment_variable",
  "incorrect_selector",
  "missing_dependency",
  "readiness_failure",
  "resource_limits",
  "liveness_probe",
  "wrong_interface",
  "port_mismatch",
  "wrong_port",
];

export interface CaseFamily {
  family: string;
  cases: { id: string; variant: string }[];
}

export function caseFamily(id: string): { family: string; variant: string } {
  const family = FAMILIES.find((prefix) => id === prefix || id.startsWith(`${prefix}_`)) ?? id;
  const variant = id === family ? "base" : id.slice(family.length + 1);
  return { family, variant };
}

export function groupCases(ids: string[]): CaseFamily[] {
  const groups = new Map<string, CaseFamily>();
  for (const id of [...ids].sort()) {
    const { family, variant } = caseFamily(id);
    const group = groups.get(family) ?? { family, cases: [] };
    group.cases.push({ id, variant });
    groups.set(family, group);
  }
  for (const group of groups.values()) group.cases.sort((a, b) => (a.variant === "base" ? -1 : b.variant === "base" ? 1 : a.variant.localeCompare(b.variant)));
  return [...groups.values()];
}

export const humanize = (value: string) => value.replaceAll("_", " ");
