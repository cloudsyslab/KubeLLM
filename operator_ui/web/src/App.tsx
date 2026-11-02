import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { Tooltip } from "radix-ui";
import { useEffect } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router";
import { RouteBoundary } from "@/components/RouteBoundary";
import { Shell } from "@/components/Shell";
import { OperatorLogin } from "@/components/OperatorLogin";
import { api, authApi } from "@/api/client";
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

function AppContent() {
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: ["operator-session"],
    queryFn: authApi.session,
    enabled: api.isLive,
    retry: false,
    staleTime: 0,
    refetchInterval: api.isLive ? 60_000 : false,
    refetchOnWindowFocus: true,
  });

  if (api.isLive && session.isPending) {
    return <main className="grid min-h-dvh place-items-center bg-bg text-[13px] text-fg-3">Checking operator session…</main>;
  }
  if (api.isLive && session.isError) {
    return (
      <main className="grid min-h-dvh place-items-center bg-bg px-5 text-center">
        <div className="grid max-w-[380px] gap-3">
          <h1 className="text-[16px] font-semibold text-fg">Operator API unavailable</h1>
          <p className="text-[13px] leading-5 text-fg-2">{session.error.message}</p>
          <button type="button" onClick={() => void session.refetch()} className="mx-auto h-8 cursor-pointer rounded-md border border-line-strong bg-surface px-3 text-[12.5px] text-fg hover:bg-surface-2">Retry</button>
        </div>
      </main>
    );
  }
  if (api.isLive && !session.data?.configured) return <OperatorLogin configured={false} />;
  if (api.isLive && !session.data?.authenticated) return <OperatorLogin configured />;

  async function logout() {
    try {
      await authApi.logout();
    } catch {
      return;
    }
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "operator-session" });
    queryClient.setQueryData(["operator-session"], {
      authenticated: false,
      configured: true,
      username: null,
    });
  }

  return (
    <Shell onLogout={api.isLive ? logout : undefined}>
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
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Tooltip.Provider delayDuration={250} skipDelayDuration={150}>
        <BrowserRouter>
          <ReplayProvider>
            <ScrollReset />
            <AppContent />
          </ReplayProvider>
        </BrowserRouter>
      </Tooltip.Provider>
    </QueryClientProvider>
  );
}
