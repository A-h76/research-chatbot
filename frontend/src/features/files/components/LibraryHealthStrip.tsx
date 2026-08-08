import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LibraryHealthSkeleton } from "@/components/common/ResearchSkeletons";
import { libraryBridgeApi } from "../libraryBridgeApi";
import { cn } from "@/lib/utils";

type Signal = {
  key: string;
  label: string;
  value: string;
  tone?: "default" | "emphasis" | "warn";
  onClick?: () => void;
};

/**
 * Slim research-progress strip — secondary to the corpus list.
 * Not a SaaS metric dashboard.
 */
export function LibraryHealthStrip({
  projectId,
  unreadCount,
  onFilterNeedsReview,
}: {
  projectId?: number | null;
  unreadCount?: number;
  onFilterNeedsReview?: () => void;
}) {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["library", "health", projectId ?? "all"],
    queryFn: () => libraryBridgeApi.health(projectId),
    staleTime: 30_000,
  });

  if (isLoading) return <LibraryHealthSkeleton />;
  if (!data || data.total === 0) return null;

  const profiles = data.by_readiness.analysed ?? 0;
  const evidenceCoverage = data.by_readiness.research_ready ?? 0;
  const needingReview =
    (data.need_pdf ?? 0) +
    (data.processing ?? 0) +
    Math.max(0, unreadCount ?? 0);
  const chatPct =
    data.total > 0 ? Math.round((data.research_ready / data.total) * 100) : 0;

  const signals: Signal[] = [
    {
      key: "papers",
      label: "Papers",
      value: data.total.toLocaleString(),
    },
    {
      key: "chat",
      label: "Chat ready",
      value: `${chatPct}%`,
      tone: chatPct >= 80 ? "emphasis" : "default",
    },
    {
      key: "evidence",
      label: "Evidence",
      value: evidenceCoverage.toLocaleString(),
    },
    {
      key: "profiles",
      label: "Profiles",
      value: profiles.toLocaleString(),
    },
    {
      key: "review",
      label: "Needs review",
      value: needingReview.toLocaleString(),
      tone: needingReview > 0 ? "warn" : "default",
      onClick:
        needingReview > 0
          ? () => {
              if (data.need_pdf > 0) onFilterNeedsReview?.();
              else navigate("/");
            }
          : undefined,
    },
  ];

  return (
    <section
      aria-label="Research progress"
      className="border-t border-border/70 pt-3"
      data-density="high"
    >
      <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Research progress
      </p>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-muted-foreground">
        {signals.map((s, i) => (
          <span key={s.key} className="inline-flex items-center gap-2">
            {i > 0 ? (
              <span className="text-border" aria-hidden>
                ·
              </span>
            ) : null}
            {s.onClick ? (
              <button
                type="button"
                onClick={s.onClick}
                className={cn(
                  "inline-flex items-baseline gap-1.5 rounded-sm transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  s.tone === "warn" && "text-sem-warn hover:text-sem-warn",
                )}
              >
                <span className="tabular-nums text-foreground/90">{s.value}</span>
                <span>{s.label}</span>
              </button>
            ) : (
              <span
                className={cn(
                  "inline-flex items-baseline gap-1.5",
                  s.tone === "emphasis" && "text-primary",
                )}
              >
                <span className="tabular-nums text-foreground/90">{s.value}</span>
                <span>{s.label}</span>
              </span>
            )}
          </span>
        ))}
      </div>
    </section>
  );
}
