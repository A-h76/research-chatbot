import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { useMe } from "@/features/profile/useMe";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Button } from "@/components/ui/button";

export function RootLayout() {
  const { data: me, isLoading, isError } = useMe();

  useEffect(() => {
    if (isLoading || me) return;
    // Full navigation — /login is a Flask template route, not a React route.
    window.location.replace("/login");
  }, [isLoading, isError, me]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background" aria-busy="true">
        <LoadingSpinner />
        <span className="sr-only">Loading workspace</span>
      </div>
    );
  }
  if (isError || !me) {
    return (
      <div
        className="flex h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center"
        role="status"
      >
        <p className="text-[13px] text-muted-foreground">Redirecting to sign in…</p>
        <Button variant="outline" size="sm" onClick={() => { window.location.href = "/login"; }}>
          Sign in
        </Button>
      </div>
    );
  }

  return (
    <AppShell me={me}>
      <Outlet />
    </AppShell>
  );
}
