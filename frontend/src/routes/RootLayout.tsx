import { Outlet } from "react-router-dom";
import { useMe } from "@/features/profile/useMe";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

export function RootLayout() {
  const { data: me, isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <LoadingSpinner />
      </div>
    );
  }
  if (isError || !me) {
    // apiClient already redirected to /login on 401
    return null;
  }

  return (
    <AppShell me={me}>
      <Outlet />
    </AppShell>
  );
}
