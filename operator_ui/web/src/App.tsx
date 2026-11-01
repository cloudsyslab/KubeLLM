import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Tooltip } from "radix-ui";
import { useEffect } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router";
import { Shell } from "@/components/Shell";
import { ReplayProvider } from "@/demo/replay";
import { OptionsRoomPage, SurfacePage } from "@/options/OptionsRoom";
import { ModelDetailPage } from "@/pages/ModelDetail";
import { ModelsPage } from "@/pages/Models";
import { PendingPage } from "@/pages/Pending";
import { RunDetailPage } from "@/pages/RunDetail";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60_000, refetchOnWindowFocus: false, retry: 1 } },
});

function ScrollReset() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

const PENDING = {
  runs: {
    eyebrow: "Evaluate",
    title: "Runs",
    description: "Every recorded run across canonical, exploratory, and local sources.",
    items: ["Searchable run history with source, technique, and model filters", "Coverage, unknown outcomes, and cost completeness per run", "Select two to eight runs to compare"],
  },
  compare: {
    eyebrow: "Evaluate",
    title: "Compare",
    description: "Put runs side by side on the cases they share.",
    items: ["Braintrust-style metric rows with per-case improvements and regressions", "Shared-case alignment and the descriptive-comparison caution", "Per-case outcome diff"],
  },
  launch: {
    eyebrow: "Operate",
    title: "New campaign",
    description: "Plan a serial campaign through the canonical runner.",
    items: ["Cases, techniques, models, and repetitions", "Planned attempt count and readiness gate", "Review-before-run confirmation"],
  },
  environment: {
    eyebrow: "Operate",
    title: "Environment",
    description: "Readiness of the selected private lane.",
    items: ["Fresh preflight result and its checks", "Explicit preparation", "Lane identity: profile, kubeconfig, RAG service, pgvector"],
  },
};

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Tooltip.Provider delayDuration={250} skipDelayDuration={150}>
        <BrowserRouter>
          <ReplayProvider>
            <ScrollReset />
            <Shell>
              <Routes>
                <Route index element={<ModelsPage />} />
                <Route path="models/:slug" element={<ModelDetailPage />} />
                <Route path="runs/:ref" element={<RunDetailPage />} />
                <Route path="runs" element={<PendingPage {...PENDING.runs} />} />
                <Route path="compare" element={<PendingPage {...PENDING.compare} />} />
                <Route path="execution" element={<SurfacePage surface="execution" eyebrow="Operate" title="Execution" description="Live view of the running campaign: progress, the current attempt's phases, and redacted output." />} />
                <Route path="launch" element={<PendingPage {...PENDING.launch} />} />
                <Route path="environment" element={<PendingPage {...PENDING.environment} />} />
                <Route path="lab" element={<SurfacePage surface="resources" eyebrow="Lab" title="Resources" description="Host, memory, disk, and GPU activity on the lab server, with the processes behind them." />} />
                <Route path="lab/topology" element={<SurfacePage surface="topology" eyebrow="Lab" title="Topology" description="Cluster profiles on the lab, read-only. Actions stay confined to the selected private lane." />} />
                <Route path="options" element={<OptionsRoomPage />} />
                <Route path="*" element={<PendingPage eyebrow="KubeLLM" title="Not found" description="This page does not exist." items={["Use the navigation to return to Models."]} />} />
              </Routes>
            </Shell>
          </ReplayProvider>
        </BrowserRouter>
      </Tooltip.Provider>
    </QueryClientProvider>
  );
}
