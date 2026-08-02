import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ChevronRight,
  FileText,
  Loader2,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/common/Toast";
import { useFiles } from "@/features/files/useFiles";
import { ApiError } from "@/lib/apiClient";
import { cn, formatDate } from "@/lib/utils";
import type { ProjectResearchPreset, ResearchClaim } from "@/types/api";
import {
  useProjectResearch,
  useProjectResearchHistory,
  useRunProjectResearch,
} from "../useProjects";

const RESEARCH_ERROR_MESSAGES: Record<string, string> = {
  too_few_ready: "At least 2 analysed papers are needed in this project.",
  too_many: "You can research at most 10 papers at once.",
  too_many_active: "Please wait until your current research finishes (max 2 at a time).",
  invalid_preset: "That research option isn’t available. Try another.",
  preset_or_query_required: "Pick a preset or type a question.",
  not_found: "This project couldn’t be found.",
  research_failed: "Research couldn’t finish. Please try again.",
  ai_disabled: "AI is temporarily disabled by the operator. Try again later.",
  token_quota_exceeded: "You've reached your monthly AI token limit.",
  cost_quota_exceeded: "You've reached your monthly AI cost limit.",
  daily_budget_exceeded: "Daily AI budget exceeded. Try again tomorrow.",
  email_unverified: "Verify your email before using AI.",
};

function researchErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return (
      RESEARCH_ERROR_MESSAGES[err.message] ||
      (err.message.includes(" ") ? err.message : "Research failed. Please try again.")
    );
  }
  if (err instanceof Error && err.message) return err.message;
  return "Research failed. Please try again.";
}

const PRESETS: { preset: ProjectResearchPreset; label: string }[] = [
  { preset: "evidence", label: "Summarise the evidence" },
  { preset: "disagree", label: "Where do these papers disagree?" },
  { preset: "methodology", label: "Which methodology is strongest?" },
  { preset: "open_questions", label: "What questions remain unanswered?" },
  { preset: "compare", label: "How do these papers compare?" },
];

function ClaimCard({ claim }: { claim: ResearchClaim }) {
  return (
    <div className="rounded-xl border border-border px-3 py-3 space-y-2">
      <p className="text-sm font-medium leading-relaxed">{claim.claim}</p>
      <ul className="space-y-2">
        {claim.support.map((s, i) => (
          <li key={`${s.paper_id}-${i}`} className="text-xs text-muted-foreground">
            <Link
              to={`/papers/${s.paper_id}`}
              className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
            >
              <FileText className="size-3 shrink-0" />
              {s.title || `Paper #${s.paper_id}`}
              <ChevronRight className="size-3" />
            </Link>
            {(s.section || s.citation) && (
              <p className="mt-0.5 text-[11px] text-muted-foreground/80">
                {[s.section, s.citation].filter(Boolean).join(" · ")}
              </p>
            )}
            {s.snippet && (
              <p className="mt-1 text-[12px] leading-relaxed text-foreground/80 line-clamp-3">
                {s.snippet}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Project research console — ask your project with structured evidence. */
export function ProjectResearchConsole({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const [freeform, setFreeform] = useState("");
  const [activeId, setActiveId] = useState<number | null>(null);

  const { data: fileData, isLoading: filesLoading } = useFiles({
    project_id: projectId,
    kind: "document",
    limit: 500,
  });

  const readyCount = useMemo(
    () => (fileData?.items ?? []).filter((f) => f.meta_status === "done").length,
    [fileData?.items],
  );

  const runResearch = useRunProjectResearch(projectId);
  const { data: result, isLoading: polling } = useProjectResearch(
    projectId,
    activeId,
  );
  const { data: history } = useProjectResearchHistory(projectId);

  const isRunning =
    runResearch.isPending || result?.status === "running" || polling;

  async function submit(
    preset: ProjectResearchPreset | null,
    query = "",
  ) {
    if (readyCount < 2) {
      toast.error("Need at least 2 analysed papers in this project.");
      return;
    }
    try {
      const r = await runResearch.mutateAsync({
        preset,
        query: preset ? undefined : query,
      });
      setActiveId(r.id);
      if (r.status === "done") {
        toast.success("Research complete");
      }
    } catch (err) {
      toast.error(researchErrorMessage(err));
    }
  }

  if (filesLoading) {
    return <Skeleton className="h-48 w-full rounded-xl" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-semibold">Ask your project…</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Cross-paper answers with supporting evidence from{" "}
          {readyCount} analysed paper{readyCount === 1 ? "" : "s"}.
        </p>
      </div>

      {readyCount < 2 ? (
        <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center space-y-2">
          <Sparkles className="mx-auto size-8 text-muted-foreground" />
          <p className="text-sm font-medium">Need at least 2 analysed papers</p>
          <p className="text-xs text-muted-foreground">
            Upload papers in the Papers tab and wait for analysis to finish.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/projects/${projectId}?tab=papers`)}
          >
            Go to Papers
          </Button>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <Button
                key={p.preset}
                variant="outline"
                size="sm"
                disabled={isRunning}
                className="h-auto whitespace-normal text-left py-2 px-3"
                onClick={() => void submit(p.preset)}
              >
                {p.label}
              </Button>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={freeform}
              onChange={(e) => setFreeform(e.target.value)}
              placeholder="Or ask a custom question…"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
              disabled={isRunning}
              onKeyDown={(e) => {
                if (e.key === "Enter" && freeform.trim()) {
                  void submit(null, freeform.trim());
                }
              }}
            />
            <Button
              disabled={isRunning || !freeform.trim()}
              onClick={() => void submit(null, freeform.trim())}
            >
              Ask
            </Button>
          </div>
        </>
      )}

      {isRunning && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Researching across project papers…
          {result?.estimated_cost_usd != null && (
            <span className="text-xs">
              · est. ${Number(result.estimated_cost_usd).toFixed(3)}
            </span>
          )}
        </div>
      )}

      {result?.status === "done" && result.estimated_cost_usd != null && (
        <p className="text-[11px] text-muted-foreground">
          Cost: est. ${Number(result.estimated_cost_usd).toFixed(3)}
          {result.actual_cost_usd != null &&
            ` · actual $${Number(result.actual_cost_usd).toFixed(3)}`}
        </p>
      )}

      {result?.status === "done" && (
        <div className="space-y-4">
          {result.summary && (
            <div className="rounded-xl border border-primary/20 bg-accent-soft/40 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Summary
              </p>
              <p className="text-sm leading-relaxed">{result.summary}</p>
            </div>
          )}
          {result.answer && (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.answer}</p>
            </div>
          )}
          {result.claims.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Claims &amp; evidence
              </h3>
              {result.claims.map((c, i) => (
                <ClaimCard key={i} claim={c} />
              ))}
            </div>
          )}
        </div>
      )}

      {result?.status === "failed" && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 space-y-2">
          <p className="text-sm text-destructive">
            Research couldn’t finish. Your papers are unchanged — try again or pick another question.
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={isRunning}
            onClick={() => {
              if (result.query) void submit(null, result.query);
              else if (result.preset)
                void submit(result.preset as ProjectResearchPreset);
            }}
          >
            Retry
          </Button>
        </div>
      )}

      {(history?.items.length ?? 0) > 0 && (
        <section className="space-y-2 border-t border-border pt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Recent research
          </h3>
          <ul className="space-y-1">
            {history!.items.map((h) => (
              <li key={h.id}>
                <button
                  type="button"
                  onClick={() => setActiveId(h.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-muted/50",
                    activeId === h.id && "bg-muted/50",
                  )}
                >
                  <Sparkles className="size-3.5 shrink-0 text-primary" />
                  <span className="min-w-0 flex-1 truncate">{h.label}</span>
                  {h.created_at && (
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      {formatDate(h.created_at)}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
