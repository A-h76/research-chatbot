import { Navigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useMe } from "@/features/profile/useMe";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { PageContainer } from "@/components/layout/PageContainer";
import type { ReactNode } from "react";

/** Client-side gate — backend still enforces @admin_required on every ops API. */
export function AdminGate({ children }: { children: ReactNode }) {
  const { data: me, isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
        <LoadingSpinner /> Checking access…
      </div>
    );
  }

  if (isError || !me) {
    return <Navigate to="/" replace />;
  }

  if (!me.is_admin) {
    return (
      <PageContainer title="Admin" description="Ops console for closed-beta operators.">
        <div className="flex items-start gap-3 rounded-xl border border-border bg-muted/30 p-5">
          <ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-medium">Admin access required</p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Your account is not marked as admin. Contact an operator if you need access.
            </p>
          </div>
        </div>
      </PageContainer>
    );
  }

  return <>{children}</>;
}
