import { Outlet } from "react-router-dom";
import { useMe } from "@/features/profile/useMe";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

export function RootLayout() {
  const { data: me, isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background" aria-busy="true">
        <LoadingSpinner />
        <span className="sr-only">Loading workspace</span>
      </div>
    );
  }
  if (isError || !me) {
    // SessionExpiredModal (App-level) handles 401; keep a calm shell while it opens.
    return (
      <div
        className="flex h-screen items-center justify-center bg-background px-6 text-center"
        role="status"
      >
        <p className="text-[13px] text-muted-foreground">
          Waiting for sign-in…
        </p>
      </div>
    );
  }

  return (
    <AppShell me={me}>
      <Outlet />
    </AppShell>
  );
}
