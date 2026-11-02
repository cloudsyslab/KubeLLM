import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "C+E+B",
    name: "Grid, story, and trace",
    idea: "Every planned attempt as a grid that fills in live. Below it, the selected attempt's story (symptom, plan, what the agent ran, the verifier, the Ground Truth verdict) beside its trace: a phase waterfall and the exact output, both in the grid's colors.",
    optimizes: "Campaign progress at a glance, what an attempt did without reading logs, and the exact output one click away.",
    tradeoff: "A tall page; the attempt box is the only place output appears, so following the whole campaign's stream means switching its scope.",
    reference: "Explorer case matrix and CI matrices, Linear activity, Braintrust traces",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./LiveCampaign")),
  },
];
