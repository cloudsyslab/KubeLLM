import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Tooltip } from "radix-ui";
import { useEffect } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router";
import { RouteBoundary } from "@/components/RouteBoundary";
import { Shell } from "@/components/Shell";
import { ReplayProvider } from "@/demo/replay";
import { OptionsRoomPage, SurfacePage } from "@/options/OptionsRoom";
import { SURFACES } from "@/options/registry";
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

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Tooltip.Provider delayDuration={250} skipDelayDuration={150}>
        <BrowserRouter>
          <ReplayProvider>
            <ScrollReset />
            <Shell>
              <RouteBoundary>
                <Routes>
                  <Route index element={<ModelsPage />} />
                  <Route path="models/:slug" element={<ModelDetailPage />} />
                  <Route path="runs/:ref" element={<RunDetailPage />} />
                  {SURFACES.filter((s) => s.path).map((s) => (
                    <Route key={s.id} path={s.path!.slice(1)} element={<SurfacePage key={s.id} surface={s.id} />} />
                  ))}
                  <Route path="options" element={<OptionsRoomPage />} />
                  <Route path="*" element={<PendingPage eyebrow="KubeLLM" title="Not found" description="This page does not exist." items={["Use the navigation to return to Models."]} />} />
                </Routes>
              </RouteBoundary>
            </Shell>
          </ReplayProvider>
        </BrowserRouter>
      </Tooltip.Provider>
    </QueryClientProvider>
  );
}
