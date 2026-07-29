import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/common/Toast";
import { evidenceApi } from "../api";
import { useEvidenceReason } from "../hooks/useEvidenceReason";
import type { EvidenceObjectDTO, ExplainResponse, Sufficiency } from "../types";

const SUFFICIENCY_COPY: Record<Sufficiency, string> = {
  sufficient: "Supported by accepted evidence",
  weak: "Only unreviewed or weak evidence",
  insufficient: "Insufficient evidence for this sentence",
};

const MEDIATOR_LABELS: Record<string, string> = {
  population_differs: "Population differs",
  dosage_differs: "Dosage differs",
  method_differs: "Method differs",
  outcome_differs: "Outcome differs",
};

export function EvidenceInspectorPanel({
  result,
  status,
  stickyText,
  documentId,
  projectId,
  onBound,
}: {
  result: ExplainResponse | null;
  status: "idle" | "loading" | "ok" | "error";
  stickyText?: string;
  documentId?: number | null;
  projectId?: number | null;
  onBound?: () => void;
}) {
  const qc = useQueryClient();
  const sufficiency = result?.sufficiency ?? "insufficient";
  const ri = useEvidenceReason({
    documentId: documentId ?? null,
    projectId: projectId ?? null,
    selectedText: stickyText || "",
    enabled: documentId != null && projectId != null,
  });

  const libraryQuery = useQuery({
    queryKey: ["evidence", "library", projectId],
    queryFn: () => evidenceApi.list(projectId as number),
    enabled: projectId != null,
  });

  const bind = useMutation({
    mutationFn: (evidenceId: number) =>
      evidenceApi.createBinding(documentId as number, {
        evidence_object_id: evidenceId,
        block_id: stickyText ? `sel_${hashText(stickyText)}` : "blk",
        selected_text: stickyText || "",
        relation: "supports",
      }),
    onSuccess: () => {
      toast.success("Evidence linked to selection");
      onBound?.();
      qc.invalidateQueries({ queryKey: ["evidence", "library", projectId] });
    },
    onError: () => toast.error("Could not link evidence"),
  });

  const review = useMutation({
    mutationFn: (payload: { id: number; status: "accepted" | "rejected" }) =>
      evidenceApi.review(payload.id, { status: payload.status }),
    onSuccess: (_data, vars) => {
      toast.success(vars.status === "accepted" ? "Evidence accepted" : "Evidence rejected");
      qc.invalidateQueries({ queryKey: ["evidence", "library", projectId] });
      onBound?.();
    },
    onError: () => toast.error("Review failed"),
  });

  const candidates = (libraryQuery.data?.items ?? []).filter((e) => e.status === "candidate");
  const linkable = (libraryQuery.data?.items ?? []).filter(
    (e) => e.status === "accepted" || e.status === "candidate",
  );
  const reduceMotion = useReducedMotion();
  const focusKey = stickyText ? `sel-${stickyText.slice(0, 48)}` : "idle";

  return (
    <aside
      className="flex w-full flex-col gap-3 border-l border-border bg-muted/20 p-3 lg:max-w-sm"
      aria-label="Evidence inspector"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight">Evidence Inspector</h2>
        {status === "loading" && (
          <span className="text-[11px] text-muted-foreground">Looking up…</span>
        )}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={focusKey}
          initial={reduceMotion ? false : { opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, x: 8 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col gap-3"
        >
      <div
        className={cn(
          "rounded-md border px-2.5 py-2 text-[12px]",
          sufficiency === "sufficient" &&
            "border-emerald-700/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200",
          sufficiency === "weak" &&
            "border-amber-700/30 bg-amber-500/10 text-amber-950 dark:text-amber-100",
          sufficiency === "insufficient" && "border-border bg-card text-muted-foreground",
        )}
        aria-live="polite"
        role="status"
      >
        {status === "idle" && !stickyText
          ? "Select text in the draft to inspect evidence."
          : SUFFICIENCY_COPY[sufficiency]}
      </div>

      {stickyText ? (
        <p className="line-clamp-3 text-[12px] text-foreground/80">
          <span className="text-muted-foreground">Selection: </span>
          {stickyText}
        </p>
      ) : null}

      {stickyText && ri.status !== "idle" ? (
        <div className="space-y-2 rounded-md border border-border bg-card p-2.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Research Intelligence
            </span>
            {ri.status === "loading" && (
              <span className="text-[10px] text-muted-foreground">Computing…</span>
            )}
          </div>
          {ri.result?.consensus?.label ? (
            <div className="flex flex-wrap gap-1">
              <span className="rounded border border-border px-1.5 py-0.5 text-[10px] uppercase">
                Consensus: {ri.result.consensus.label}
              </span>
              <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                +{ri.result.consensus.supporting ?? 0} / −{ri.result.consensus.contradicting ?? 0} / ~
                {ri.result.consensus.neutral ?? 0}
              </span>
            </div>
          ) : null}
          {ri.result?.conflict?.has_conflict ? (
            <div className="flex flex-wrap gap-1">
              {(ri.result.conflict.mediators ?? []).length > 0 ? (
                (ri.result.conflict.mediators ?? []).map((m) => (
                  <span
                    key={m}
                    className="rounded border border-amber-700/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-950 dark:text-amber-100"
                  >
                    {MEDIATOR_LABELS[m] || m}
                  </span>
                ))
              ) : (
                <span className="text-[10px] text-muted-foreground">
                  Conflict present (mediators uncoded)
                </span>
              )}
            </div>
          ) : null}
          {ri.result?.reasoning?.summary_code ? (
            <p className="text-[11px] text-muted-foreground">
              Summary:{" "}
              <span className="font-medium text-foreground">
                {ri.result.reasoning.summary_code}
              </span>
              {ri.result.reasoning.sufficiency
                ? ` · ${ri.result.reasoning.sufficiency}`
                : ""}
            </p>
          ) : null}
          {ri.result?.reasoning?.steps?.length ? (
            <ol className="list-decimal space-y-0.5 pl-4 text-[10px] text-muted-foreground">
              {ri.result.reasoning.steps.map((step, i) => (
                <li key={`${step.step}-${i}`}>
                  <span className="font-medium text-foreground/80">{step.step}</span>: {step.detail}
                </li>
              ))}
            </ol>
          ) : null}
          {ri.status === "error" && (
            <p className="text-[10px] text-muted-foreground">Could not load RI reason stage.</p>
          )}
        </div>
      ) : null}

      {result?.evidence?.length ? (
        <ul className="flex flex-col gap-2">
          {result.evidence.map((ev) => (
            <EvidenceObjectCard
              key={ev.id}
              evidence={ev}
              onAccept={
                ev.status === "candidate"
                  ? () => review.mutate({ id: ev.id, status: "accepted" })
                  : undefined
              }
              onReject={
                ev.status === "candidate"
                  ? () => review.mutate({ id: ev.id, status: "rejected" })
                  : undefined
              }
            />
          ))}
        </ul>
      ) : status === "ok" ? (
        <p className="text-[12px] text-muted-foreground">
          No linked evidence for this selection. Link an object below, or extract from Research
          Ready papers.
        </p>
      ) : null}

      {stickyText && documentId != null && linkable.length > 0 ? (
        <div className="space-y-1.5 border-t border-border pt-2">
          <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Link to selection
          </h3>
          <ul className="max-h-40 space-y-1 overflow-auto">
            {linkable.slice(0, 12).map((ev) => (
              <li key={ev.id} className="flex items-start justify-between gap-2 text-[11px]">
                <span className="line-clamp-2 text-foreground/80">{ev.claim || ev.quote}</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 shrink-0 px-1.5 text-[10px]"
                  disabled={bind.isPending}
                  onClick={() => bind.mutate(ev.id)}
                >
                  Link
                </Button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {candidates.length > 0 && !result?.evidence?.length ? (
        <p className="text-[11px] text-muted-foreground">
          {candidates.length} candidate object{candidates.length === 1 ? "" : "s"} in project —
          accept after review.
        </p>
      ) : null}

      {result?.chain?.length ? (
        <div className="space-y-1">
          <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Chain
          </h3>
          <ol className="list-decimal space-y-1 pl-4 text-[11px] text-muted-foreground">
            {result.chain.map((step, i) => (
              <li key={`${step.step}-${i}`}>{step.detail}</li>
            ))}
          </ol>
        </div>
      ) : null}
        </motion.div>
      </AnimatePresence>
    </aside>
  );
}

function EvidenceObjectCard({
  evidence,
  onAccept,
  onReject,
}: {
  evidence: EvidenceObjectDTO;
  onAccept?: () => void;
  onReject?: () => void;
}) {
  return (
    <li className="rounded-md border border-border bg-card p-2.5 text-[12px]">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        <span className="font-medium text-foreground">{evidence.claim}</span>
        {evidence.status === "candidate" && (
          <span className="rounded border border-amber-600/40 px-1 py-0.5 text-[10px] uppercase text-amber-800 dark:text-amber-200">
            Candidate
          </span>
        )}
        <span className="rounded border border-border px-1 py-0.5 text-[10px] uppercase text-muted-foreground">
          {evidence.confidence_band}
        </span>
        <span className="rounded border border-border px-1 py-0.5 text-[10px] uppercase text-muted-foreground">
          {evidence.relation}
        </span>
      </div>
      <p className="line-clamp-2 text-muted-foreground">&ldquo;{evidence.quote}&rdquo;</p>
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        {evidence.file_title || `File ${evidence.file_id}`}
        {evidence.page != null ? ` · p. ${evidence.page}` : ""}
        {evidence.study_type ? ` · ${evidence.study_type}` : ""}
      </p>
      {(onAccept || onReject) && (
        <div className="mt-2 flex gap-1">
          {onAccept && (
            <Button size="sm" variant="outline" className="h-6 px-1.5 text-[10px]" onClick={onAccept}>
              Accept
            </Button>
          )}
          {onReject && (
            <Button size="sm" variant="ghost" className="h-6 px-1.5 text-[10px]" onClick={onReject}>
              Reject
            </Button>
          )}
        </div>
      )}
    </li>
  );
}

function hashText(text: string): string {
  let h = 0;
  for (let i = 0; i < Math.min(text.length, 64); i += 1) {
    h = (h * 31 + text.charCodeAt(i)) >>> 0;
  }
  return h.toString(16);
}
