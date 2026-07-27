import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

type Props = {
  children: ReactNode;
  /** Optional compact fallback (e.g. inside a panel). */
  fallback?: ReactNode;
};

type State = { error: Error | null };

/**
 * D9 / M11 — App-level React error boundary.
 * Catches render failures so one bad tab doesn’t blank the whole SPA.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary]", error, info.componentStack);
    }
  }

  private reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    return (
      <div
        role="alert"
        className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-6 text-center"
      >
        <div className="space-y-2">
          <h1 className="text-lg font-semibold tracking-tight">Something went wrong</h1>
          <p className="max-w-md text-[13px] text-muted-foreground">
            Soro hit an unexpected error in this view. Your library and projects are safe —
            try reloading, or go home and continue from there.
          </p>
          {import.meta.env.DEV && (
            <pre className="mt-3 max-w-lg overflow-auto rounded-md border border-border bg-muted/40 p-3 text-left font-mono text-[11px] text-destructive">
              {this.state.error.message}
            </pre>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Button variant="outline" onClick={this.reset}>
            Try again
          </Button>
          <Button onClick={() => { window.location.href = "/"; }}>
            Go home
          </Button>
          <Button variant="ghost" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      </div>
    );
  }
}
