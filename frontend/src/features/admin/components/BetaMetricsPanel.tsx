import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { adminOpsApi } from "../api";

const PERIODS = [7, 14, 30] as const;

export function BetaMetricsPanel() {
  const [days, setDays] = useState<(typeof PERIODS)[number]>(7);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "ops", "beta-metrics", days],
    queryFn: () => adminOpsApi.betaMetrics(days),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
        <LoadingSpinner /> Loading metrics…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-destructive">
        Could not load beta metrics.{" "}
        <button type="button" className="underline" onClick={() => refetch()}>
          Retry
        </button>
      </p>
    );
  }

  const counts = [
    { label: "New users", value: data.counts.new_users },
    { label: "Returning", value: data.counts.returning_users },
    { label: "New projects", value: data.counts.new_projects },
    { label: "Papers analysed", value: data.counts.papers_analysed },
    { label: "Research runs", value: data.counts.research_runs },
    { label: "Memories promoted", value: data.counts.memories_promoted },
  ];

  const funnel = [
    { label: "Users with projects", value: data.funnel_all_time.users_with_projects },
    {
      label: "2+ analysed papers",
      value: data.funnel_all_time.users_2plus_analysed_papers,
    },
    { label: "Research run", value: data.funnel_all_time.users_with_research_run },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        {PERIODS.map((d) => (
          <Button
            key={d}
            size="sm"
            variant={days === d ? "default" : "outline"}
            onClick={() => setDays(d)}
          >
            {d}d
          </Button>
        ))}
        <span className="text-xs text-muted-foreground">
          Since {new Date(data.since).toLocaleDateString()}
        </span>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Period counts</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {counts.map((c) => (
            <div key={c.label} className="rounded-xl border border-border px-4 py-3">
              <p className="text-xs text-muted-foreground">{c.label}</p>
              <p className="mt-1 text-2xl font-semibold tracking-tight">{c.value}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Activation funnel (all-time)</p>
        <p className="mb-2 text-[12px] text-muted-foreground">{data.targets.activation}</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {funnel.map((c) => (
            <div key={c.label} className="rounded-xl border border-border px-4 py-3">
              <p className="text-xs text-muted-foreground">{c.label}</p>
              <p className="mt-1 text-xl font-semibold tracking-tight">{c.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
