import { useParams } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useFile, useAnalyzeDocument } from "../useFiles";

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

export function FileDetailPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const id = fileId ? Number(fileId) : null;

  const { data: file, isLoading: fileLoading } = useFile(id);
  const analyze = useAnalyzeDocument();

  if (fileLoading) {
    return (
      <PageContainer title="File">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </PageContainer>
    );
  }

  if (!file) {
    return (
      <PageContainer title="File">
        <p className="text-sm text-muted-foreground">File not found.</p>
      </PageContainer>
    );
  }

  const d = analyze.data?.analysis;

  return (
    <PageContainer
      title={file.title || file.name}
      description={file.authors || undefined}
      actions={
        <Button
          onClick={() => id != null && analyze.mutate(id)}
          disabled={analyze.isPending || id == null}
          className="gap-2"
        >
          {analyze.isPending ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
          {analyze.isPending ? "Analyzing…" : "Analyze with AI"}
        </Button>
      }
    >
      <div className="mx-auto max-w-3xl space-y-6">

        {analyze.isError && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
            {analyze.error instanceof Error ? analyze.error.message : "Analysis failed"}
          </div>
        )}

        {d && (
          <div className="space-y-6">
            <Separator />

            {d.executive_summary && (
              <div className="rounded-xl border border-primary/10 bg-accent-soft/60 p-4">
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-primary">Summary</p>
                <p className="text-sm leading-relaxed">{d.executive_summary}</p>
              </div>
            )}

            <div className="grid gap-6 sm:grid-cols-2">
              <AnalysisBlock label="Research Problem" value={d.problem_statement} />
              <AnalysisBlock label="Research Objective" value={d.research_objective} />
              <AnalysisBlock label="Methodology" value={d.methodology} />
              {d.dataset && <AnalysisBlock label="Dataset" value={d.dataset} />}
              <AnalysisBlock label="Experiments" value={d.experiments} />
              <AnalysisBlock label="Results" value={d.results} />
            </div>

            <Separator />

            <div className="grid gap-6 sm:grid-cols-2">
              <BulletList label="Key Findings" items={d.key_contributions} />
              <BulletList label="Strengths" items={d.strengths} />
              <BulletList label="Limitations" items={d.limitations} />
              <BulletList label="Future Work" items={d.future_work} />
            </div>

            {d.keywords?.length ? (
              <>
                <Separator />
                <div className="flex flex-wrap gap-2">
                  {d.keywords.map((kw) => (
                    <Badge key={kw} variant="outline" className="text-xs font-normal">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>
    </PageContainer>
  );
}
