import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/api/client";
import { Mark } from "./Shell";

export function OperatorLogin({ configured }: { configured: boolean }) {
  const [password, setPassword] = useState("");
  const queryClient = useQueryClient();
  const login = useMutation({
    mutationFn: authApi.login,
    onSuccess: () => {
      setPassword("");
      queryClient.setQueryData(["operator-session"], {
        authenticated: true,
        configured: true,
        username: "Operator",
      });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    login.mutate(password);
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-bg px-5 py-10">
      <section className="w-full max-w-[390px] rounded-lg border border-line bg-surface p-6 shadow-sm sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <Mark className="size-8 text-fg" />
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-fg">KubeLLM Operator</h1>
            <p className="label mt-1">Private lab console</p>
          </div>
        </div>
        {configured ? (
          <>
            <p className="mb-5 text-[13px] leading-5 text-fg-2">Sign in to view lab data and operate the selected private lane.</p>
            <form className="grid gap-3" onSubmit={submit}>
              <label htmlFor="operator-password" className="text-[12px] font-medium text-fg-2">Operator password</label>
              <input
                id="operator-password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-10 rounded-md border border-line-strong bg-bg px-3 text-[13px] text-fg outline-none focus:border-fg-3"
              />
              {login.error && <p role="alert" className="text-[12px] text-warn">{login.error.message}</p>}
              <button
                type="submit"
                disabled={login.isPending || !password}
                className="mt-1 h-9 cursor-pointer rounded-md bg-fg px-3 text-[13px] font-medium text-bg transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {login.isPending ? "Signing in…" : "Sign in"}
              </button>
            </form>
          </>
        ) : (
          <div className="grid gap-3 text-[13px] leading-5 text-fg-2">
            <p>The private operator login has not been initialized on this server.</p>
            <p>Run <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px]">make operator-ui-auth</code> on the server, then reload this page.</p>
          </div>
        )}
      </section>
    </main>
  );
}
