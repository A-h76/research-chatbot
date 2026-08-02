import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Gauge } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { toast } from "@/components/common/Toast";
import { formatApiFailure } from "@/lib/apiErrors";
import { adminOpsApi } from "../api";

export function QuotasPanel() {
  const qc = useQueryClient();
  const [userId, setUserId] = useState("");
  const [lookedUpId, setLookedUpId] = useState<number | null>(null);
  const [tokenLimit, setTokenLimit] = useState("");
  const [costLimit, setCostLimit] = useState("");
  const [storageMb, setStorageMb] = useState("");
  const [plan, setPlan] = useState("");

  const disabledQ = useQuery({
    queryKey: ["admin", "ops", "quotas-disabled"],
    queryFn: adminOpsApi.getQuotasDisabled,
  });

  const analyticsQ = useQuery({
    queryKey: ["admin", "ops", "quota-analytics"],
    queryFn: () => adminOpsApi.quotaAnalytics(30),
  });

  const usageQ = useQuery({
    queryKey: ["admin", "ops", "quota-user", lookedUpId],
    queryFn: () => adminOpsApi.getUserQuota(lookedUpId as number),
    enabled: lookedUpId != null,
  });

  const toggleDisabled = useMutation({
    mutationFn: (disabled: boolean) => adminOpsApi.setQuotasDisabled(disabled),
    onSuccess: (res) => {
      qc.setQueryData(["admin", "ops", "quotas-disabled"], {
        quotas_disabled: res.quotas_disabled,
      });
      toast.success(res.quotas_disabled ? "Quotas disabled globally" : "Quotas enabled");
    },
    onError: (err) => toast.error(formatApiFailure(err, "Update failed")),
  });

  const patch = useMutation({
    mutationFn: () => {
      if (lookedUpId == null) throw new Error("No user selected");
      const body: {
        monthly_token_limit?: number;
        monthly_cost_limit?: number;
        storage_limit_bytes?: number;
        plan?: string;
      } = {};
      if (tokenLimit.trim()) body.monthly_token_limit = Number(tokenLimit);
      if (costLimit.trim()) body.monthly_cost_limit = Number(costLimit);
      if (storageMb.trim()) body.storage_limit_bytes = Math.round(Number(storageMb) * 1024 * 1024);
      if (plan.trim()) body.plan = plan.trim();
      return adminOpsApi.patchUserQuota(lookedUpId, body);
    },
    onSuccess: (res) => {
      qc.setQueryData(["admin", "ops", "quota-user", lookedUpId], res.usage);
      toast.success("Limits updated");
    },
    onError: (err) => toast.error(formatApiFailure(err, "Update failed")),
  });

  const reset = useMutation({
    mutationFn: () => {
      if (lookedUpId == null) throw new Error("No user selected");
      return adminOpsApi.resetUserQuota(lookedUpId);
    },
    onSuccess: (res) => {
      qc.setQueryData(["admin", "ops", "quota-user", lookedUpId], res.usage);
      toast.success("Usage reset for billing period");
    },
    onError: (err) => toast.error(formatApiFailure(err, "Reset failed")),
  });

  function lookup() {
    const id = Number(userId);
    if (!Number.isFinite(id) || id <= 0) {
      toast.error("Enter a numeric user id");
      return;
    }
    setLookedUpId(id);
  }

  const usage = usageQ.data;
  const tokens = usage?.tokens;
  const globalOff = disabledQ.data?.quotas_disabled === true;

  return (
    <div className="space-y-5">
      <div
        className={`flex items-start gap-3 rounded-xl border p-4 ${
          globalOff ? "border-amber-500/40 bg-amber-500/5" : "border-border bg-muted/20"
        }`}
      >
        <Gauge className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">Global quotas kill</p>
              <p className="mt-0.5 text-[13px] text-muted-foreground">
                When on, entitlement checks are skipped for all users (closed-beta escape hatch).
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="quotas-off" className="text-xs text-muted-foreground">
                {globalOff ? "Quotas off" : "Quotas on"}
              </Label>
              <Switch
                id="quotas-off"
                checked={globalOff}
                disabled={toggleDisabled.isPending || disabledQ.isLoading}
                onCheckedChange={(checked) => toggleDisabled.mutate(checked)}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border p-4 space-y-3">
        <p className="text-sm font-medium">Per-user limits</p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <Label htmlFor="uid" className="text-xs">
              User id
            </Label>
            <Input
              id="uid"
              className="h-8 w-28"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="42"
            />
          </div>
          <Button size="sm" className="h-8" onClick={lookup}>
            Load
          </Button>
        </div>

        {usageQ.isFetching ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoadingSpinner /> Loading usage…
          </div>
        ) : null}

        {usageQ.isError ? (
          <p className="text-sm text-destructive">
            {formatApiFailure(usageQ.error, "Could not load user quota")}
          </p>
        ) : null}

        {usage && lookedUpId != null ? (
          <div className="space-y-3">
            <p className="text-[13px] text-muted-foreground">
              Plan: {String(usage.plan || "—")} · Tokens:{" "}
              {(tokens?.used ?? usage.token_used ?? 0).toLocaleString()} /{" "}
              {(tokens?.limit ?? usage.token_limit ?? 0).toLocaleString()}
              {tokens?.percent != null ? ` (${tokens.percent}%)` : ""}
              {tokens?.warning ? " · soft warning" : ""}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1">
                <Label className="text-xs">Monthly token limit</Label>
                <Input
                  className="h-8"
                  value={tokenLimit}
                  onChange={(e) => setTokenLimit(e.target.value)}
                  placeholder={String(tokens?.limit ?? usage.token_limit ?? "")}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Monthly cost limit (USD)</Label>
                <Input
                  className="h-8"
                  value={costLimit}
                  onChange={(e) => setCostLimit(e.target.value)}
                  placeholder="optional"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Storage limit (MB)</Label>
                <Input
                  className="h-8"
                  value={storageMb}
                  onChange={(e) => setStorageMb(e.target.value)}
                  placeholder="optional"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Plan</Label>
                <Input
                  className="h-8"
                  value={plan}
                  onChange={(e) => setPlan(e.target.value)}
                  placeholder={String(usage.plan || "free")}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                disabled={patch.isPending}
                onClick={() => patch.mutate()}
              >
                Save limits
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={reset.isPending}
                onClick={() => {
                  if (window.confirm(`Reset usage counters for user ${lookedUpId}?`)) {
                    reset.mutate();
                  }
                }}
              >
                Reset usage
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-border p-4">
        <p className="text-sm font-medium">Usage analytics (30d)</p>
        {analyticsQ.isLoading ? (
          <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <LoadingSpinner /> Loading…
          </div>
        ) : analyticsQ.isError ? (
          <p className="mt-2 text-sm text-muted-foreground">Analytics unavailable.</p>
        ) : (
          <div className="mt-2 space-y-2 text-[12px] text-muted-foreground">
            <p>Total units: {(analyticsQ.data?.total_units ?? 0).toLocaleString()}</p>
            <ul className="space-y-0.5">
              {(analyticsQ.data?.by_operation ?? []).slice(0, 8).map((row) => (
                <li key={row.operation}>
                  {row.operation}: {row.units.toLocaleString()}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
