import { Link } from "react-router-dom";
import {
  Layers,
  Network,
  Scale,
  Tags,
  BookOpen,
  type LucideIcon,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usePipeline, usePipelinePhase } from "@/features/pipeline";
import { mapStructure } from "../mappers/structure";
import { mapClassification } from "../mappers/classification";
import { mapEntities } from "../mappers/entities";
import { mapEvidence } from "../mappers/evidence";
import { mapKnowledgeGraph } from "../mappers/graph";
import { buildWorkspaceRail, workspaceHref, type WorkspaceTab } from "../mappers/chat";
import { WorkspaceReferenceChips } from "./WorkspaceReferenceChips";
import { useMemo } from "react";

const TAB_LINKS: { tab: WorkspaceTab; label: string; icon: LucideIcon }[] = [
  { tab: "structure", label: "Structure", icon: BookOpen },
  { tab: "evidence", label: "Evidence", icon: Scale },
  { tab: "entities", label: "Entities", icon: Tags },
  { tab: "graph", label: "Graph", icon: Network },
  { tab: "classification", label: "Profile", icon: Layers },
];

/**
 * Paper Chat evidence rail — jump into workspace tabs; curated highlights only.
 */
export function PaperChatEvidenceRail({ fileId }: { fileId: number }) {
  const { pipeline, isLoading: pipelineLoading } = usePipeline(fileId);

  const has = (phase: string) =>
    pipeline != null &&
    (pipeline.phases.includes(phase as never) || phase in (pipeline.phase_results ?? {}));

  const duQ = usePipelinePhase(fileId, "document_understanding", {
    enabled: has("document_understanding"),
  });
  const clfQ = usePipelinePhase(fileId, "classification", { enabled: has("classification") });
  const ctxQ = usePipelinePhase(fileId, "analysis_context", { enabled: has("analysis_context") });
  const medQ = usePipelinePhase(fileId, "medical_understanding", {
    enabled: has("medical_understanding"),
  });
  const egQ = usePipelinePhase(fileId, "evidence_grading", { enabled: has("evidence_grading") });
  const kgQ = usePipelinePhase(fileId, "knowledge_graph", { enabled: has("knowledge_graph") });

  const references = useMemo(() => {
    const structure = mapStructure(
      duQ.data?.result ?? pipeline?.phase_results?.document_understanding ?? null,
    );
    const classification = mapClassification(
      clfQ.data?.result ?? pipeline?.phase_results?.classification ?? null,
      ctxQ.data?.result ?? pipeline?.phase_results?.analysis_context ?? null,
    );
    const entities = mapEntities(
      medQ.data?.result ?? pipeline?.phase_results?.medical_understanding ?? null,
    );
    const evidence = mapEvidence(
      egQ.data?.result ?? pipeline?.phase_results?.evidence_grading ?? null,
    );
    const graph = mapKnowledgeGraph(
      kgQ.data?.result ?? pipeline?.phase_results?.knowledge_graph ?? null,
    );
    return buildWorkspaceRail({
      fileId,
      structure,
      classification,
      entities,
      evidence,
      graph,
    });
  }, [fileId, pipeline, duQ.data, clfQ.data, ctxQ.data, medQ.data, egQ.data, kgQ.data]);

  const loading =
    pipelineLoading ||
    duQ.isLoading ||
    clfQ.isLoading ||
    medQ.isLoading ||
    egQ.isLoading ||
    kgQ.isLoading;

  return (
    <aside
      aria-label="Workspace evidence rail"
      className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden"
    >
      <div className="min-h-0 flex-1 space-y-3 overflow-x-hidden overflow-y-auto pr-0.5">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Workspace
          </h2>
          <p className="mt-1 text-[12px] leading-snug text-muted-foreground">
            Open analysis tabs. Chat stays paper-grounded.
          </p>
        </div>

        <nav aria-label="Paper tabs" className="flex flex-col gap-0.5">
          {TAB_LINKS.map(({ tab, label, icon: Icon }) => (
            <Link
              key={tab}
              to={workspaceHref(fileId, tab)}
              className={cn(
                "flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-foreground",
                "hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              )}
            >
              <Icon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>

        {loading && references.length === 0 ? (
          <div className="space-y-2" aria-busy="true">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-4/5" />
          </div>
        ) : references.length > 0 ? (
          <div className="min-w-0 border-t border-border pt-3">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Highlights
            </p>
            <WorkspaceReferenceChips references={references} />
          </div>
        ) : null}
      </div>
    </aside>
  );
}
