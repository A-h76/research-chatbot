import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { adminOpsApi } from "../api";

export function SecurityEventsPanel() {
  const [filter, setFilter] = useState("");
  const [applied, setApplied] = useState<string | undefined>(undefined);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["admin", "ops", "security-events", applied],
    queryFn: () => adminOpsApi.securityEvents(100, applied),
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[14rem] flex-1 space-y-1">
          <Label htmlFor="event-filter" className="text-xs">
            Filter by event name
          </Label>
          <Input
            id="event-filter"
            placeholder="e.g. admin_ai_kill_switch"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") setApplied(filter.trim() || undefined);
            }}
          />
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={isFetching}
          onClick={() => setApplied(filter.trim() || undefined)}
        >
          Apply
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setFilter("");
            setApplied(undefined);
            refetch();
          }}
        >
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
          <LoadingSpinner /> Loading events…
        </div>
      ) : isError ? (
        <p className="text-sm text-destructive">
          Could not load security events.{" "}
          <button type="button" className="underline" onClick={() => refetch()}>
            Retry
          </button>
        </p>
      ) : items.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">No events in this window.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[40rem] text-left text-[13px]">
            <thead className="border-b border-border bg-muted/30 text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">When</th>
                <th className="px-3 py-2 font-medium">Event</th>
                <th className="px-3 py-2 font-medium">User</th>
                <th className="px-3 py-2 font-medium">IP</th>
                <th className="px-3 py-2 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ev) => (
                <tr key={ev.id} className="border-b border-border/60 align-top last:border-0">
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">
                    {ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2 font-medium">{ev.event}</td>
                  <td className="px-3 py-2">{ev.user_id ?? "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">{ev.ip || "—"}</td>
                  <td className="max-w-xs px-3 py-2">
                    <pre className="max-h-24 overflow-auto whitespace-pre-wrap break-all font-mono text-[11px] text-muted-foreground">
                      {JSON.stringify(ev.detail ?? {}, null, 0)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
