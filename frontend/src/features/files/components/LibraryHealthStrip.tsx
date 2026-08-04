import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LibraryHealthSkeleton } from "@/components/common/ResearchSkeletons";
import { libraryBridgeApi } from "../libraryBridgeApi";
import { cn } from "@/lib/utils";

type Metric = {
  label: string;
  value: number;
  hint?: string;
  tone?: "default" | "emphasis" | "warn";
};

/**
 * Research Readiness — actionable corpus overview (not a dashboard chart card).
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

  const metrics: Metric[] = [
    { label: "Papers", value: data.total },
    {
      label: "Chat Ready",
      value: data.research_ready,
      tone: data.research_ready > 0 ? "emphasis" : "default",
      hint: "Indexed and ready to ask",
    },
    {
      label: "Research Profiles",
      value: profiles,
      hint: "Analysed papers",
    },
    {
      label: "Evidence Coverage",
      value: evidenceCoverage,
      hint: "Papers with extractable evidence",
    },
    {
      label: "Needs Review",
      value: needingReview,
      tone: needingReview > 0 ? "warn" : "default",
      hint: "PDF missing, processing, or unread",
    },
  ];

  const continueTarget =
    data.need_pdf > 0
      ? { label: "Need full text", run: () => onFilterNeedsReview?.() }
      : data.processing > 0
        ? { label: "Continue Research", run: () => navigate("/home") }
        : data.research_ready > 0
          ? { label: "Continue Research", run: () => navigate("/home") }
          : { label: "Continue Research", run: () => navigate("/library") };

  return (
    <section
      aria-label="Research readiness"
      className="border-b border-border/70 pb-5"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-[13px] font-semibold tracking-tight text-foreground">
            Research readiness
          </h2>
          <p className="mt-0.5 text-[12px] text-muted-foreground">
            How far your corpus is toward grounded research work.
          </p>
        </div>
        <Button
          size="sm"
          className="h-8 gap-1.5 text-[12px]"
          onClick={continueTarget.run}
        >
          {continueTarget.label}
          <ArrowRight className="size-3.5" />
        </Button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
        {metrics.map((m) => (
          <div key={m.label} className="min-w-0">
            <p
              className={cn(
                "text-[22px] font-semibold tracking-tight tabular-nums leading-none",
                m.tone === "emphasis" && "text-primary",
                m.tone === "warn" && needingReview > 0 && "text-amber-600 dark:text-amber-400",
                m.tone === "default" && "text-foreground",
              )}
              title={m.hint}
            >
              {m.value.toLocaleString()}
            </p>
            <p className="mt-1.5 text-[11px] font-medium text-muted-foreground">
              {m.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
