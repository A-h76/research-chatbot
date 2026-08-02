import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldOff, ShieldCheck } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { toast } from "@/components/common/Toast";
import { adminOpsApi } from "../api";
import { useState } from "react";

export function KillSwitchPanel() {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "ops", "settings"],
    queryFn: adminOpsApi.getSettings,
  });
  const [budget, setBudget] = useState("");

  const patch = useMutation({
    mutationFn: adminOpsApi.patchSettings,
    onSuccess: (snap) => {
      qc.setQueryData(["admin", "ops", "settings"], snap);
      toast.success("Ops settings updated");
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Update failed"),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
        <LoadingSpinner /> Loading kill switch…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-destructive">
        Could not load settings.{" "}
        <button type="button" className="underline" onClick={() => refetch()}>
          Retry
        </button>
      </p>
    );
  }

  const disabled = data.ai_disabled;
  const daily = data.daily ?? {};

  return (
    <div className="space-y-5">
      <div
        className={`flex items-start gap-3 rounded-xl border p-4 ${
          disabled
            ? "border-destructive/40 bg-destructive/5"
            : "border-border bg-muted/20"
        }`}
      >
        {disabled ? (
          <ShieldOff className="mt-0.5 size-5 shrink-0 text-destructive" />
        ) : (
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-600" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">AI kill switch</p>
              <p className="mt-0.5 text-[13px] text-muted-foreground">
                When on, all non-admin AI calls are blocked immediately (no deploy).
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="ai-kill" className="text-xs text-muted-foreground">
                {disabled ? "AI disabled" : "AI enabled"}
              </Label>
              <Switch
                id="ai-kill"
                checked={disabled}
                disabled={patch.isPending}
                onCheckedChange={(checked) => patch.mutate({ ai_disabled: checked })}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border p-4">
        <p className="text-sm font-medium">Daily AI budget</p>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Spend today: ${(daily.spend_usd ?? 0).toFixed(2)}
          {daily.budget_usd != null && daily.budget_usd > 0
            ? ` / $${daily.budget_usd.toFixed(2)} (${Math.round(daily.pct ?? 0)}%)`
            : " · no hard budget set"}
          {daily.paused ? " · paused" : ""}
        </p>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <Label htmlFor="budget" className="text-xs">
              Budget USD / day
            </Label>
            <Input
              id="budget"
              type="number"
              min={0}
              step={0.5}
              className="w-36"
              placeholder={String(daily.budget_usd ?? 0)}
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
            />
          </div>
          <Button
            size="sm"
            disabled={patch.isPending || budget === ""}
            onClick={() => {
              const amount = Number(budget);
              if (Number.isNaN(amount) || amount < 0) {
                toast.error("Enter a valid budget");
                return;
              }
              patch.mutate({ daily_ai_budget_usd: amount });
              setBudget("");
            }}
          >
            Save budget
          </Button>
        </div>
      </div>
    </div>
  );
}
