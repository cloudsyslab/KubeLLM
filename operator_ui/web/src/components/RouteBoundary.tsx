import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { PageHeader } from "@/components/ui";

interface State {
  error: Error | null;
}

class Boundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Page failed to render", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="grid gap-6">
        <PageHeader eyebrow="KubeLLM" title="This page failed to render" description="The rest of the app still works. Try the page again, or go back to Models." />
        <div className="grid gap-4 rounded-lg border border-line bg-surface px-5 py-4">
          <pre className="overflow-x-auto font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-fg-2">{error.message}</pre>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => this.setState({ error: null })}
              className="inline-flex h-8 cursor-pointer items-center rounded-md bg-fg px-3 text-[12.5px] font-medium text-bg hover:bg-fg/85"
            >
              Try again
            </button>
            <Link to="/" className="inline-flex h-8 items-center rounded-md border border-line px-3 text-[12.5px] text-fg-2 hover:bg-surface-2 hover:text-fg">
              Models
            </Link>
          </div>
        </div>
      </div>
    );
  }
}

// One page crashing keeps the shell (navigation, active work, health) up.
// Keyed by path, so moving to another page clears the error.
export function RouteBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return <Boundary key={pathname}>{children}</Boundary>;
}
