import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { FunnelChart } from "@/components/charts/funnel-chart";
import { Ring } from "@/components/charts/ring";
import { RingCenter } from "@/components/charts/ring-center";
import { RingChart } from "@/components/charts/ring-chart";
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

/** Cumulative funnel: Imported → PDF → Analysed+ → Research Ready */
function buildReadinessFunnel(data: LibraryHealth) {
  const { by_readiness: r, total, research_ready } = data;
  const withPdf = Math.max(0, total - (r.metadata_only ?? 0));
  const analysedPlus =
    (r.analysed ?? 0) + (r.indexed ?? 0) + (r.research_ready ?? 0);
  return [
    { label: "Imported", value: total, color: "var(--chart-4)" },
    { label: "PDF", value: withPdf, color: "var(--chart-3)" },
    { label: "Analysed", value: analysedPlus, color: "var(--chart-2)" },
    { label: "Ready", value: research_ready, color: "var(--primary)" },
  ].filter((s) => s.value > 0 || s.label === "Imported");
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

  const funnelData = useMemo(
    () => (data && data.total > 0 ? buildReadinessFunnel(data) : []),
    [data],
  );

  if (!data || data.total === 0) return null;

  const lastSync = data.sync.connections
    .map((c) => c.last_synced_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  const lastRun = data.sync.runs[0];
  const readyPct = Math.round((data.research_ready / data.total) * 100);

  return (
    <div className="rounded-lg border border-border bg-muted/20 px-3 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-medium">
            Research readiness
            <span className="ml-2 font-normal text-muted-foreground">
              {data.research_ready}/{data.total} ready
              {data.need_pdf > 0 ? ` · ${data.need_pdf} need PDF` : ""}
              {data.processing > 0 ? ` · ${data.processing} processing` : ""}
            </span>
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            {formatSyncAge(lastSync)}
            {lastRun?.status === "error" && lastRun.error
              ? ` · Last sync error`
              : lastRun
                ? ` · Last run +${lastRun.created}/~${lastRun.updated}`
                : ""}
          </p>
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
        <div className="size-[80px] shrink-0" title={`${readyPct}% Research Ready`}>
          <RingChart
            data={[
              {
                label: "Ready",
                value: readyPct,
                maxValue: 100,
                color: "var(--primary)",
              },
            ]}
            size={80}
            strokeWidth={9}
            baseInnerRadius={22}
            animationDuration={700}
          >
            <Ring index={0} showGlow={false} />
            <RingCenter suffix="%" defaultLabel="Ready" />
          </RingChart>
        </div>
      </div>

      {funnelData.length >= 2 && (
        <div className="mt-3 h-[88px] w-full">
          <FunnelChart
            data={funnelData}
            orientation="horizontal"
            showPercentage={false}
            showValues
            showLabels
            labelLayout="grouped"
            edges="straight"
            gap={3}
            className="h-full w-full"
            staggerDelay={0.06}
          />
        </div>
      )}
    </div>
  );
}
