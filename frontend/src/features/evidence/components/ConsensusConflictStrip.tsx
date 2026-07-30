import { cn } from "@/lib/utils";

export type ConsensusProductLabel = "Agree" | "Disagree" | "Mixed" | "Weak evidence";

export type ConflictWhyCard = {
  code: string;
  title: string;
  why: string;
  supporting_signals?: string[];
  contradicting_signals?: string[];
};

export type ConsensusConflictStripProps = {
  status: "idle" | "loading" | "ok" | "error";
  consensus?: {
    label?: string;
    product_label?: string;
    supporting?: number;
    contradicting?: number;
    neutral?: number;
  } | null;
  conflict?: {
    has_conflict?: boolean;
    mediators?: string[];
    mediator_explanations?: Array<{ code: string; title: string; why: string }>;
    links?: Array<{
      a_id: number;
      b_id: number;
      mediators?: string[];
      why?: ConflictWhyCard[];
      unexplained?: boolean;
    }>;
    metrics?: {
      mediated_pair_count?: number;
      unexplained_pair_count?: number;
      mediation_coverage?: number | null;
    };
    product_summary?: string | null;
  } | null;
  compact?: boolean;
  className?: string;
};

const PRODUCT_STYLES: Record<string, string> = {
  Agree: "border-emerald-700/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200",
  Disagree: "border-rose-700/30 bg-rose-500/10 text-rose-950 dark:text-rose-100",
  Mixed: "border-amber-700/30 bg-amber-500/10 text-amber-950 dark:text-amber-100",
  "Weak evidence": "border-border bg-muted/40 text-muted-foreground",
};

/** RI-003 / RI-004 product strip — consensus stance + contradiction WHY. */
export function ConsensusConflictStrip({
  status,
  consensus,
  conflict,
  compact = false,
  className,
}: ConsensusConflictStripProps) {
  if (status === "idle") return null;

  const product = consensus?.product_label || mapOrdinalToProduct(consensus?.label);
  const whyLinks = (conflict?.links ?? []).filter((l) => (l.why && l.why.length > 0) || l.unexplained);
  const unexplained = conflict?.metrics?.unexplained_pair_count ?? 0;

  return (
    <div
      className={cn("space-y-2 rounded-md border border-border bg-card p-2.5", className)}
      aria-label="Research intelligence consensus and contradictions"
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Research Intelligence
        </span>
        {status === "loading" && (
          <span className="text-[10px] text-muted-foreground">Computing…</span>
        )}
        {status === "error" && (
          <span className="text-[10px] text-muted-foreground">Could not load consensus.</span>
        )}
      </div>

      {status === "ok" && product ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className={cn(
              "rounded border px-1.5 py-0.5 text-[11px] font-medium",
              PRODUCT_STYLES[product] || PRODUCT_STYLES["Weak evidence"],
            )}
          >
            {product}
          </span>
          <span className="text-[10px] text-muted-foreground">
            +{consensus?.supporting ?? 0} agree · −{consensus?.contradicting ?? 0} disagree · ~
            {consensus?.neutral ?? 0} neutral
          </span>
          {consensus?.label ? (
            <span className="text-[10px] text-muted-foreground/70">({consensus.label})</span>
          ) : null}
        </div>
      ) : null}

      {status === "ok" && conflict?.has_conflict ? (
        <div className="space-y-1.5">
          <p className="text-[11px] font-medium text-foreground">Why they disagree</p>
          {conflict.product_summary ? (
            <p className="text-[10px] text-muted-foreground">{conflict.product_summary}</p>
          ) : null}
          {(conflict.mediator_explanations ?? []).length > 0 ? (
            <ul className="space-y-1">
              {(conflict.mediator_explanations ?? []).map((m) => (
                <li key={m.code} className="text-[11px] text-foreground/90">
                  <span className="font-medium">{m.title}</span>
                  <span className="text-muted-foreground"> — {m.why}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[10px] text-muted-foreground">
              Conflict present but mediators uncoded.
            </p>
          )}
          {!compact && whyLinks.slice(0, 4).map((link) => (
            <div
              key={`${link.a_id}-${link.b_id}`}
              className="rounded border border-border/80 bg-muted/20 px-2 py-1.5"
            >
              <p className="text-[10px] text-muted-foreground">
                Evidence #{link.a_id} ↔ #{link.b_id}
                {link.unexplained ? " · unexplained" : ""}
              </p>
              {(link.why ?? []).map((card) => (
                <p key={card.code} className="mt-0.5 text-[10px] text-foreground/85">
                  <span className="font-medium">{card.title}:</span> {card.why}
                  {card.supporting_signals?.length || card.contradicting_signals?.length ? (
                    <span className="text-muted-foreground">
                      {" "}
                      (
                      {(card.supporting_signals ?? []).slice(0, 2).join(", ") || "—"}
                      {" vs "}
                      {(card.contradicting_signals ?? []).slice(0, 2).join(", ") || "—"}
                      )
                    </span>
                  ) : null}
                </p>
              ))}
            </div>
          ))}
          {unexplained > 0 ? (
            <p className="text-[10px] text-amber-800 dark:text-amber-200">
              {unexplained} pair{unexplained === 1 ? "" : "s"} still unexplained — review
              methods and samples manually.
            </p>
          ) : null}
        </div>
      ) : null}

      {status === "ok" && consensus && !conflict?.has_conflict && product === "Agree" ? (
        <p className="text-[10px] text-muted-foreground">No coded contradictions in this set.</p>
      ) : null}
    </div>
  );
}

function mapOrdinalToProduct(label?: string): ConsensusProductLabel | null {
  if (!label) return null;
  if (label === "opposed") return "Disagree";
  if (label === "contested") return "Mixed";
  if (label === "none") return "Weak evidence";
  if (label === "strong" || label === "moderate") return "Agree";
  return null;
}
