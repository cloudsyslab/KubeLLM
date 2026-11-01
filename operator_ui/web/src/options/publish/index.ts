import { lazy } from "react";
import type { OptionDef } from "../registry";

export const OPTIONS: OptionDef[] = [
  {
    id: "a",
    letter: "A",
    name: "Review panel",
    idea: "The preview's summary beside a collapsible file tree and the exact catalog lines, with one acknowledgment and the publish job inline.",
    optimizes: "A complete, honest review built only from what the preview API already returns (counts, models, paths, hashes).",
    tradeoff: "File contents are described, not shown; one checkbox is light friction for a push to a shared repository.",
    reference: "GitHub pull request files view, Vercel deployment summary",
    recommended: true,
    component: lazy(() => import("./ReviewPanel")),
  },
  {
    id: "b",
    letter: "B",
    name: "Full review",
    idea: "Three panes: file tree, a preview of the selected file (exact README and catalog diffs, illustrative JSON), and a six-point checklist ending in typing the pack name.",
    optimizes: "Maximum care before writing to data/: every claim confirmed, content inspected.",
    tradeoff: "Heavy for a routine export, and showing file contents needs a new read endpoint for the private preview.",
    reference: "GitHub repository deletion, Braintrust dataset review",
    component: lazy(() => import("./FullReview")),
  },
  {
    id: "c",
    letter: "C",
    name: "Receipt",
    idea: "A narrow receipt that walks preview, review, publish, and done, with totals as line items and the details folded away.",
    optimizes: "Phones and a quick, readable sign-off; makes the preview step explicit.",
    tradeoff: "The file list is folded into summaries; no per-file browsing.",
    reference: "Stripe receipts and checkout",
    component: lazy(() => import("./Receipt")),
  },
];
