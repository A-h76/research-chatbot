import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { adminOpsApi } from "../api";

/** Compact worker heartbeat chip for Admin header. */
export function WorkerHealthChip() {
  const { data, isError, isFetching } = useQuery({
    queryKey: ["admin", "worker-health"],
    queryFn: adminOpsApi.workerHealth,
    refetchInterval: 30_000,
    retry: 1,
  });

  const status = isError ? "unknown" : data?.status || "unknown";
  const tone =
    status === "ok"
      ? "border-emerald-600/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200"
      : status === "down"
        ? "border-destructive/40 bg-destructive/10 text-destructive"
        : "border-border bg-muted/40 text-muted-foreground";

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
        tone,
      )}
      title={
        data?.age_seconds != null
          ? `Heartbeat age ${Math.round(data.age_seconds)}s`
          : "Worker queue health"
      }
    >
      <Activity className={cn("size-3", isFetching && "animate-pulse")} />
      Worker: {status}
      {data?.age_seconds != null && status === "ok" ? (
        <span className="opacity-70">· {Math.round(data.age_seconds)}s</span>
      ) : null}
    </div>
  );
}
