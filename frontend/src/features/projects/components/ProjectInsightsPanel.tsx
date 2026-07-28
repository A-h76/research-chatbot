import { Link } from "react-router-dom";
import {
  Archive,
  FileText,
  Pin,
  PinOff,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/common/Toast";
import { cn, formatDate } from "@/lib/utils";
import type { ProjectMemory, ProjectMemoryKind } from "@/types/api";
import {
  useDeleteProjectMemory,
  usePatchProjectMemory,
  useProjectInsights,
  useProjectMemory,
} from "../useProjects";

const KIND_SECTIONS: { kind: ProjectMemoryKind | "pinned"; title: string }[] = [
  { kind: "pinned", title: "Pinned" },
  { kind: "finding", title: "Recent findings" },
  { kind: "contradiction", title: "Contradictions" },
  { kind: "open_question", title: "Open questions" },
  { kind: "claim", title: "Claims" },
];

function KindBadge({ kind }: { kind: string }) {
  return (
    <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium capitalize text-muted-foreground">
      {kind.replace("_", " ")}
    </span>
  );
}

function MemoryCard({
  memory,
  onPin,
  onArchive,
  pending,
}: {
  memory: ProjectMemory;
  onPin: () => void;
  onArchive: () => void;
  pending: boolean;
}) {
  const papers = memory.payload?.paper_ids ?? [];
  return (
    <div className="rounded-xl border border-border px-3 py-3 space-y-2">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <KindBadge kind={memory.kind} />
            <span className="text-[10px] text-muted-foreground capitalize">
              {memory.source}
            </span>
            {memory.created_at && (
              <span className="text-[10px] text-muted-foreground/70">
                {formatDate(memory.created_at)}
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed">{memory.fact}</p>
        </div>
        <div className="flex shrink-0 gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            disabled={pending}
            onClick={onPin}
            aria-label={memory.pinned ? "Unpin" : "Pin"}
          >
            {memory.pinned ? (
              <PinOff className="size-3.5" />
            ) : (
              <Pin className="size-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            disabled={pending}
            onClick={onArchive}
            aria-label="Archive"
          >
            <Archive className="size-3.5" />
          </Button>
        </div>
      </div>
      {papers.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {papers.map((pid) => (
            <Link
              key={pid}
              to={`/papers/${pid}`}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5",
                "text-[11px] text-primary hover:underline",
              )}
            >
              <FileText className="size-3" /> Paper #{pid}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/** Insights (DerivedAnalysis) + Research Memory — distinct models, one tab. */
export function ProjectInsightsPanel({ projectId }: { projectId: number }) {
  const {
    data: insights,
    isLoading: insightsLoading,
    isError: insightsError,
    refetch: refetchInsights,
  } = useProjectInsights(projectId);
  const {
    data: memoryData,
    isLoading: memoryLoading,
    isError: memoryError,
    refetch: refetchMemory,
  } = useProjectMemory(projectId);
  const patchMemory = usePatchProjectMemory(projectId);
  const deleteMemory = useDeleteProjectMemory(projectId);

  const isLoading = insightsLoading || memoryLoading;
  const memories = (memoryData?.items ?? []).filter((m) => m.source !== "chat");

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-16 w-full rounded-xl" />
        <Skeleton className="h-16 w-full rounded-xl" />
      </div>
    );
  }

  if (insightsError || memoryError) {
    return (
      <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center space-y-3">
        <p className="text-sm font-medium">Couldn’t load insights &amp; memory</p>
        <p className="text-xs text-muted-foreground">Check your connection and try again.</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            void refetchInsights();
            void refetchMemory();
          }}
        >
          Retry
        </Button>
      </div>
    );
  }

  const insightItems = insights?.items ?? [];

  async function togglePin(m: ProjectMemory) {
    try {
      await patchMemory.mutateAsync({
        memoryId: m.id,
        action: m.pinned ? "unpin" : "pin",
      });
    } catch {
      toast.error("Could not update pin");
    }
  }

  async function archive(m: ProjectMemory) {
    try {
      await patchMemory.mutateAsync({ memoryId: m.id, action: "archive" });
      toast.success("Archived");
    } catch {
      toast.error("Could not archive");
    }
  }

  function sectionItems(section: (typeof KIND_SECTIONS)[number]) {
    if (section.kind === "pinned") {
      return memories.filter((m) => m.pinned);
    }
    return memories.filter((m) => m.kind === section.kind && !m.pinned);
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-sm font-semibold">Insights &amp; Memory</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Insights are research runs. Memory is durable knowledge promoted from
          research — not your notes, not chat history.
        </p>
      </div>

      {/* Research memory sections */}
      <div className="space-y-6">
        {KIND_SECTIONS.map((section) => {
          const items = sectionItems(section);
          if (items.length === 0 && section.kind !== "finding") return null;
          return (
            <section key={section.kind} className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {section.title}
                {items.length > 0 ? ` (${items.length})` : ""}
              </h3>
              {items.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  Run project research to promote findings here.
                </p>
              ) : (
                <div className="space-y-2">
                  {items.map((m) => (
                    <MemoryCard
                      key={m.id}
                      memory={m}
                      pending={patchMemory.isPending || deleteMemory.isPending}
                      onPin={() => void togglePin(m)}
                      onArchive={() => void archive(m)}
                    />
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>

      {/* DerivedAnalysis insights — separate mental model */}
      <section className="space-y-2 border-t border-border pt-6">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Research runs ({insightItems.length})
        </h3>
        <p className="text-xs text-muted-foreground">
          Full compare / gaps / research outputs (not the same as durable memory).
        </p>
        {insightItems.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-6 py-8 text-center space-y-2">
            <Sparkles className="mx-auto size-7 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No research runs yet.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {insightItems.map((insight) => (
              <div
                key={insight.id}
                className="rounded-xl border border-border px-3 py-3 space-y-1.5"
              >
                <div className="flex items-center gap-2">
                  <Sparkles className="size-4 shrink-0 text-primary" />
                  <p className="text-sm font-medium">{insight.title}</p>
                  <span className="ml-auto text-[10px] capitalize text-muted-foreground">
                    {insight.kind}
                  </span>
                </div>
                {insight.preview && (
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {insight.preview}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
