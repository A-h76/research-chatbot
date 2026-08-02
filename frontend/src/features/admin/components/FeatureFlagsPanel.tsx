import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Switch } from "@/components/ui/switch";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { toast } from "@/components/common/Toast";
import { adminOpsApi, type FeatureFlagItem } from "../api";

export function FeatureFlagsPanel() {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "ops", "feature-flags"],
    queryFn: adminOpsApi.listFeatureFlags,
  });

  const setFlag = useMutation({
    mutationFn: ({
      flag_name,
      enabled,
      rollout_pct,
    }: {
      flag_name: string;
      enabled: boolean;
      rollout_pct?: number | null;
    }) =>
      adminOpsApi.setFeatureFlag(flag_name, {
        enabled,
        rollout_pct: rollout_pct ?? null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "ops", "feature-flags"] });
      toast.success("Feature flag updated");
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Update failed"),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
        <LoadingSpinner /> Loading flags…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-destructive">
        Could not load feature flags.{" "}
        <button type="button" className="underline" onClick={() => refetch()}>
          Retry
        </button>
      </p>
    );
  }

  // Show global rows only (user_id null) — per-user overrides stay API-only for V1.
  const globals = data.flags.filter((f) => f.user_id == null);

  return (
    <div className="space-y-3">
      <p className="text-[13px] text-muted-foreground">
        Kill or gradually roll out gated paths. Defaults are fail-open until you write a DB row.
      </p>
      {globals.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">No flags registered.</p>
      ) : (
        globals.map((flag: FeatureFlagItem) => (
          <div
            key={flag.flag_name}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border px-4 py-3"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium">{flag.flag_name}</p>
              <p className="mt-0.5 text-[12px] text-muted-foreground">
                {flag.description || "—"}
                {flag.rollout_pct != null ? ` · rollout ${flag.rollout_pct}%` : ""}
                {flag.source === "default" ? " · default" : ""}
              </p>
            </div>
            <Switch
              checked={flag.enabled}
              disabled={setFlag.isPending}
              onCheckedChange={(checked) =>
                setFlag.mutate({
                  flag_name: flag.flag_name,
                  enabled: checked,
                  rollout_pct: flag.rollout_pct,
                })
              }
            />
          </div>
        ))
      )}
    </div>
  );
}
