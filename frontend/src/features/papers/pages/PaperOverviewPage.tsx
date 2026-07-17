import { useParams, useNavigate } from "react-router-dom";
import {
  FileText, BookOpen, Calendar,
  BarChart3, Lightbulb,
  ArrowRight, Tag, RefreshCw, MessageSquare, ChevronLeft,
  BookMarked, CheckCircle2, Loader2, StickyNote, ExternalLink, Quote,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useFile, usePaperAnalysis, usePatchFile, useRefreshAnalysis } from "@/features/files/useFiles";
import { useCitationFromPaper } from "@/features/citations/useCitations";
import { useCreateConversation } from "@/features/chat/hooks/useConversation";
import { toast } from "@/components/common/Toast";
import type { ReadingStatus } from "@/types/api";

// ─── tiny sub-components ────────────────────────────────────────────────────

function SectionHeader({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-primary">{icon}</span>
      <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </h3>
    </div>
  );
}

function AnalysisBlock({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="text-sm leading-relaxed text-foreground/90">{value}</p>
    </div>
  );
}

function BulletList({ label, items }: { label: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-foreground/90">
            <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary/60" />
            <span className="leading-relaxed">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SkeletonSection() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
    </div>
  );
}

// Reading status pill — cycles unread → reading → read on click
const STATUS_CONFIG: Record<ReadingStatus, { label: string; color: string; next: ReadingStatus }> = {
  unread:  { label: "Unread",  color: "bg-muted text-muted-foreground border-border", next: "reading" },
  reading: { label: "Reading", color: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800", next: "read" },
  read:    { label: "Read ✓",  color: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800", next: "unread" },
};

function ReadingStatusBadge({
  status,
  onChange,
}: {
  status: ReadingStatus;
  onChange: (s: ReadingStatus) => void;
}) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unread;
  return (
    <button
      onClick={() => onChange(cfg.next)}
      title="Click to cycle reading status"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors hover:opacity-80",
        cfg.color,
      )}
    >
      <BookMarked className="size-3" />
      {cfg.label}
    </button>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export function PaperOverviewPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const navigate = useNavigate();
  const id = fileId ? Number(fileId) : null;

  const { data: file, isLoading: fileLoading } = useFile(id);
  const { data: analysis, isLoading: analysisLoading } = usePaperAnalysis(id);
  const patchFile            = usePatchFile();
  const citationFromPaper    = useCitationFromPaper();
  const refreshAnalysis = useRefreshAnalysis();
  const createConversation = useCreateConversation();

  // Notes are now in the dedicated Notes workspace (M10)

  // Derive display title
  const displayTitle = file?.title || file?.name || "Paper";
  const analysisDone = analysis?.status === "done";
  const analysisRunning = analysis?.status === "pending" || analysis?.status === "running";

  function handleStatusChange(s: ReadingStatus) {
    if (!id) return;
    patchFile.mutate(
      { id, body: { reading_status: s } },
      { onSuccess: () => toast.success(`Marked as ${s}`) },
    );
  }

  function handleChatWithPaper() {
    if (!id) return;
    // Navigate to the dedicated paper chat page — it creates the conversation
    navigate(`/papers/${id}/chat`);
  }

  // ── Loading skeleton ──
  if (fileLoading) {
    return (
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-10 space-y-8">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
          <div className="grid grid-cols-2 gap-4 pt-4">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonSection key={i} />)}
          </div>
        </div>
      </div>
    );
  }

  if (!file) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Paper not found.
      </div>
    );
  }

  const d = analysis?.data ?? {};

  return (
    <div className="scrollbar-thin h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-3xl px-6 py-8 space-y-8">

        {/* ── Back nav ── */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft className="size-4" /> Knowledge Library
        </button>

        {/* ── Header ── */}
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-accent-soft">
              <FileText className="size-6 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold leading-snug tracking-tight">
                {displayTitle}
              </h1>
              {file.authors && (
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{file.authors}</p>
              )}
            </div>
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2">
            <ReadingStatusBadge
              status={(file.reading_status as ReadingStatus) ?? "unread"}
              onChange={handleStatusChange}
            />
            {file.year && (
              <span className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground">
                <Calendar className="size-3" /> {file.year}
              </span>
            )}
            {file.venue && (
              <span className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground">
                <BookOpen className="size-3" />
                <span className="max-w-[18ch] truncate">{file.venue}</span>
              </span>
            )}
            {file.doi && (
              <a
                href={`https://doi.org/${file.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs text-primary hover:underline"
              >
                DOI <ExternalLink className="size-3" />
              </a>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={handleChatWithPaper}
              disabled={createConversation.isPending}
              className="gap-2"
            >
              <MessageSquare className="size-4" />
              Chat with this paper
            </Button>
            <Button
              variant="outline"
              onClick={async () => {
                if (!id) return;
                const r = await citationFromPaper.mutateAsync({ fileId: id, projectId: file.project_id });
                if (r.existing) toast.success("Already in your citations.");
                else toast.success("Saved to citations.");
              }}
              disabled={citationFromPaper.isPending || !file?.title}
              className="gap-2"
              title={!file?.title ? "Metadata extraction pending" : "Save to citations"}
            >
              <Quote className="size-4" />
              Save to citations
            </Button>
            <Button
              variant="outline"
              onClick={() => refreshAnalysis.mutate(id!)}
              disabled={refreshAnalysis.isPending || analysisRunning}
              className="gap-2"
            >
              {analysisRunning ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              {analysisRunning ? "Analysing…" : "Re-analyse"}
            </Button>
          </div>
        </div>

        <Separator />

        {/* ── Abstract ── */}
        {file.abstract && (
          <section className="space-y-3">
            <SectionHeader icon={<FileText className="size-4" />} label="Abstract" />
            <p className="text-sm leading-relaxed text-foreground/80">{file.abstract}</p>
          </section>
        )}

        {/* ── Analysis ── */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <SectionHeader icon={<BarChart3 className="size-4" />} label="Paper Analysis" />
            {analysisRunning && (
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="size-3 animate-spin" /> Generating analysis…
              </span>
            )}
            {analysisDone && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-3" /> Complete
              </span>
            )}
          </div>

          {analysisLoading || analysisRunning ? (
            <div className="space-y-5">
              {Array.from({ length: 5 }).map((_, i) => <SkeletonSection key={i} />)}
            </div>
          ) : analysisDone ? (
            <div className="space-y-6">

              {/* Executive Summary */}
              {d.executive_summary && (
                <div className="rounded-xl bg-accent-soft/60 border border-primary/10 p-4">
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
                    Summary
                  </p>
                  <p className="text-sm leading-relaxed">{d.executive_summary}</p>
                </div>
              )}

              {/* Two-col grid for structured fields */}
              <div className="grid gap-6 sm:grid-cols-2">
                <AnalysisBlock label="Research Problem" value={d.problem_statement} />
                <AnalysisBlock label="Research Objective" value={d.research_objective} />
                <AnalysisBlock label="Methodology" value={d.methodology} />
                {d.dataset && <AnalysisBlock label="Dataset" value={d.dataset} />}
                <AnalysisBlock label="Experiments" value={d.experiments} />
                <AnalysisBlock label="Results" value={d.results} />
              </div>

              <Separator />

              {/* Lists */}
              <div className="grid gap-6 sm:grid-cols-2">
                <BulletList label="Key Contributions" items={d.key_contributions} />
                <BulletList label="Strengths" items={d.strengths} />
                <BulletList label="Limitations" items={d.limitations} />
                <BulletList label="Future Work" items={d.future_work} />
              </div>

              {/* Keywords */}
              {d.keywords?.length ? (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <SectionHeader icon={<Tag className="size-4" />} label="Keywords" />
                    <div className="flex flex-wrap gap-2">
                      {d.keywords.map((kw) => (
                        <Badge key={kw} variant="outline" className="text-xs font-normal">
                          {kw}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}

              {/* Important Terms */}
              {d.important_terms && Object.keys(d.important_terms).length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <SectionHeader icon={<Lightbulb className="size-4" />} label="Important Terms" />
                    <dl className="grid gap-3 sm:grid-cols-2">
                      {Object.entries(d.important_terms).map(([term, def]) => (
                        <div key={term} className="rounded-lg border border-border bg-muted/40 p-3">
                          <dt className="text-xs font-semibold text-foreground">{term}</dt>
                          <dd className="mt-0.5 text-xs text-muted-foreground leading-relaxed">{def}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </>
              )}
            </div>
          ) : analysis?.status === "failed" ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
              <p className="font-medium">Analysis failed</p>
              {analysis.error && <p className="mt-1 text-xs opacity-80">{analysis.error}</p>}
              <Button
                size="sm"
                variant="outline"
                className="mt-3"
                onClick={() => refreshAnalysis.mutate(id!)}
              >
                Try again
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              Analysis will appear here once processing is complete.
            </p>
          )}
        </section>

        <Separator />

        {/* ── User tags ── */}
        {file.tags?.length > 0 && (
          <section className="space-y-3">
            <SectionHeader icon={<Tag className="size-4" />} label="Your Tags" />
            <div className="flex flex-wrap gap-2">
              {file.tags.map((t) => (
                <Badge key={t} variant="secondary" className="text-xs">
                  {t}
                </Badge>
              ))}
            </div>
          </section>
        )}

        {/* ── Notes ── */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <SectionHeader icon={<StickyNote className="size-4" />} label="Notes" />
            <button
              onClick={() => navigate(`/notes?file_id=${id}`)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
            >
              View all <ArrowRight className="size-3" />
            </button>
          </div>
          <div className="rounded-xl border border-border bg-muted/30 p-4">
            <p className="text-sm text-muted-foreground">
              Notes for this paper are stored in your{" "}
              <button
                onClick={() => navigate(`/notes?file_id=${id}`)}
                className="font-medium text-primary hover:underline"
              >
                Notes workspace
              </button>
              .
            </p>
            <button
              onClick={() => navigate(`/notes?file_id=${id}`)}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-accent-soft px-3 py-1.5 text-xs font-medium text-primary hover:bg-accent-soft/80 transition-colors"
            >
              <StickyNote className="size-3.5" />
              Open notes for this paper
            </button>
          </div>
        </section>

        {/* ── CTA footer ── */}
        <div className="rounded-2xl border border-primary/20 bg-accent-soft/50 p-5">
          <div className="flex items-start gap-4">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <MessageSquare className="size-5 text-primary" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">Chat with this paper</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Ask questions, request explanations, or explore specific sections. The AI answers using only this paper's content.
              </p>
            </div>
            <Button
              onClick={handleChatWithPaper}
              disabled={createConversation.isPending}
              size="sm"
              className="shrink-0 gap-1.5"
            >
              Open <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </div>

        {/* bottom breathing room */}
        <div className="h-8" />
      </div>
    </div>
  );
}
