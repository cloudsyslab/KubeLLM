import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "chosen",
    letter: "C+B",
    name: "Guided receipt with a full review",
    idea: "Prepare, review, publish, done, as guided steps with the receipt beside them; the review step opens into the full review (every file, the exact README and catalog lines, a six-point checklist and the typed pack name) when wanted.",
    optimizes: "A quick, readable sign-off by default, and full inspection one click away without leaving the path; the final step says plainly what is committed and that it is pushed.",
    tradeoff: "Two confirmations before a push (the review and the publish step); the full review's file contents need a read endpoint for the private preview.",
    reference: "Stripe receipts and checkout, GitHub repository deletion, the New campaign steps",
    recommended: true,
    chosen: true,
    component: lazy(() => import("./GuidedPublish")),
  },
];
