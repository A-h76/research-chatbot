import { Loader2, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useEvidenceExtract } from "../hooks/useEvidenceExtract";

/**
 * Research Ready → Evidence Extraction Pipeline (not "Evidence Engine").
 * Creates candidate EvidenceObjects for the Evidence Platform.
 */
export function ExtractEvidenceButton({
  projectId,
  fileId,
  readiness,
  className,
  size = "sm",
  stopPropagation = false,
}: {
  projectId: number | null | undefined;
  fileId: number;
  readiness?: string | null;
  className?: string;
  size?: "sm" | "default";
  stopPropagation?: boolean;
}) {
  const extract = useEvidenceExtract();
  const ready = readiness === "research_ready" || readiness == null;
  const disabled = projectId == null || extract.isPending || !ready;

  return (
    <Button
      type="button"
      size={size}
      variant="outline"
      disabled={disabled}
      title={
        projectId == null
          ? "Assign this paper to a project to extract evidence"
          : !ready
            ? "Paper must be Research Ready before Evidence Extraction"
            : "Run Evidence Extraction Pipeline → candidate EvidenceObjects"
      }
      className={cn(
        size === "sm" ? "h-7 gap-1.5 px-2 text-[11px]" : "gap-2",
        className,
      )}
      onClick={(e) => {
        if (stopPropagation) e.stopPropagation();
        if (projectId == null) return;
        extract.mutate({ projectId, fileId });
      }}
    >
      {extract.isPending ? (
        <Loader2 className="size-3.5 animate-spin" />
      ) : (
        <FlaskConical className="size-3.5" />
      )}
      Extract evidence
    </Button>
  );
}
