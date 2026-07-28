import { useQuery } from "@tanstack/react-query";
import { libraryBridgeApi, type LibraryHealth } from "../libraryBridgeApi";

const STEPS: { key: keyof LibraryHealth["by_readiness"]; label: string }[] = [
  { key: "metadata_only", label: "Metadata" },
  { key: "pdf_attached", label: "PDF" },
  { key: "analysed", label: "Analysed" },
  { key: "indexed", label: "Indexed" },
  { key: "research_ready", label: "Ready" },
];

function formatSyncAge(iso: string | null | undefined): string {
  if (!iso) return "Never synced";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "Never synced";
  const mins = Math.round((Date.now() - t) / 60_000);
  if (mins < 1) return "Synced just now";
  if (mins < 60) return `Synced ${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `Synced ${hrs}h ago`;
  return `Synced ${Math.round(hrs / 24)}d ago`;
}

export function LibraryHealthStrip({
  projectId,
}: {
  projectId?: number | null;
}) {
  const { data } = useQuery({
    queryKey: ["library", "health", projectId ?? "all"],
    queryFn: () => libraryBridgeApi.health(projectId),
    staleTime: 30_000,
  });

  if (!data || data.total === 0) return null;

  const lastSync = data.sync.connections
    .map((c) => c.last_synced_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  const lastRun = data.sync.runs[0];

  return (
    <div className="rounded-lg border border-border bg-muted/20 px-3 py-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[13px] font-medium">
          Research readiness
          <span className="ml-2 font-normal text-muted-foreground">
            {data.research_ready}/{data.total} ready
            {data.need_pdf > 0 ? ` · ${data.need_pdf} need PDF` : ""}
            {data.processing > 0 ? ` · ${data.processing} processing` : ""}
          </span>
        </p>
        <p className="text-[11px] text-muted-foreground">
          {formatSyncAge(lastSync)}
          {lastRun?.status === "error" && lastRun.error
            ? ` · Last sync error`
            : lastRun
              ? ` · Last run +${lastRun.created}/~${lastRun.updated}`
              : ""}
        </p>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {STEPS.map((s) => {
          const n = data.by_readiness[s.key] ?? 0;
          if (n === 0 && s.key === "indexed") return null;
          return (
            <span
              key={s.key}
              className="inline-flex items-center gap-1 rounded border border-border bg-background px-1.5 py-0.5 text-[11px] text-muted-foreground"
              title={s.label}
            >
              <span className="text-foreground">{n}</span>
              {s.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
