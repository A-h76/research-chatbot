import {
  BarChart3, Sparkles, Clock, CheckCircle2, Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { DomainSelector } from "@/features/analysis/components/DomainSelector";
import { MetadataInput, type MetadataInputValue } from "@/features/analysis/components/MetadataInput";
import { AnalysisOutput } from "@/features/analysis/components/AnalysisOutput";
import { ResearchProgressStage } from "@/features/writing/components/ResearchProgressStage";
import type { PaperAnalysis, UserFile } from "@/types/api";

const PAPER_ANALYSIS_STAGES = [
  "Reading paper structure",
  "Extracting key claims",
  "Writing analysis",
] as const;

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

function SkeletonSection() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
    </div>
  );
}

/** Existing Analysis Output experience — M4 Narrative tab (no behaviour changes). */
export function PaperNarrativeTab({
  file,
  analysis,
  analysisLoading,
  analysisDone,
  generating,
  stillProcessing,
  notReadyError,
  domain,
  onDomainChange,
  detectedDomain,
  userQuery,
  onUserQueryChange,
  metadata,
  onMetadataChange,
  onAnalyze,
  analyzeError,
  analyzeErrorMessage,
  markdown,
}: {
  file: UserFile;
  analysis: PaperAnalysis | undefined;
  analysisLoading: boolean;
  analysisDone: boolean;
  generating: boolean;
  stillProcessing: boolean;
  notReadyError: boolean;
  domain: string | null;
  onDomainChange: (v: string | null) => void;
  detectedDomain?: string;
  userQuery: string;
  onUserQueryChange: (v: string) => void;
  metadata: MetadataInputValue;
  onMetadataChange: (patch: Partial<MetadataInputValue>) => void;
  onAnalyze: () => void;
  analyzeError: boolean;
  analyzeErrorMessage: string;
  markdown: string;
}) {
  return (
    <section className="space-y-5" data-density="medium">
      <div className="flex items-center justify-between">
        <SectionHeader icon={<BarChart3 className="size-4" />} label="Single Paper Analysis" />
        {analysisDone && !generating && (
          <span className="flex items-center gap-1.5 text-xs text-sem-ready">
            <CheckCircle2 className="size-3" /> Analysis ready
          </span>
        )}
      </div>

      {generating ? (
        <ResearchProgressStage
          active
          stages={PAPER_ANALYSIS_STAGES}
          liveMetric="Single-paper analysis from Research Ready content"
        />
      ) : null}

      {stillProcessing || notReadyError ? (
        <div className="flex items-center gap-2 rounded-md border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
          <Clock className="size-4 shrink-0" />
          This paper is still being processed. Analysis will be available once extraction completes.
        </div>
      ) : (
        <div className="space-y-4 rounded-md border border-border bg-muted/15 p-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:items-start">
            <div className="space-y-1.5">
              <DomainSelector
                value={domain}
                onChange={onDomainChange}
                detectedDomain={detectedDomain}
                disabled={generating}
              />
              <p className="text-xs text-muted-foreground">
                Select a domain for deeper, discipline-specific analysis. Auto-detect chooses the best option.
              </p>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="analysis-user-query">Your question (optional)</Label>
              <Input
                id="analysis-user-query"
                value={userQuery}
                onChange={(e) => onUserQueryChange(e.target.value)}
                placeholder="e.g., How does this compare to prior work?"
                disabled={generating}
              />
            </div>
          </div>

          <MetadataInput
            value={metadata}
            onChange={onMetadataChange}
            disabled={generating}
            documentMetadata={{
              title: file.title,
              authors: file.authors,
              venue: file.venue,
              year: file.year,
            }}
          />

          <Button onClick={onAnalyze} disabled={generating} className="gap-2">
            {generating ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            {generating
              ? "Writing analysis…"
              : analysisDone
                ? "Re-analyze paper"
                : "Analyze paper"}
          </Button>

          {analyzeError && !notReadyError && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
              {analyzeErrorMessage}
            </div>
          )}
        </div>
      )}

      {analysisLoading || generating ? (
        <div className="space-y-5">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonSection key={i} />)}
        </div>
      ) : analysisDone ? (
        <AnalysisOutput analysis={markdown} />
      ) : analysis?.status === "failed" ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
          <p className="font-medium">Analysis failed</p>
          {analysis.error && <p className="mt-1 text-xs opacity-80">{analysis.error}</p>}
          <Button size="sm" variant="outline" className="mt-3" onClick={onAnalyze}>
            Try again
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic">
          Analysis will appear here once processing is complete.
        </p>
      )}
    </section>
  );
}
