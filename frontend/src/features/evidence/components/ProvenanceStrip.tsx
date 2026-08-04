/**
 * Confidence Doctrine — every evidence object should expose provenance.
 * Compact inspector strip; hairline structure only (Border Doctrine).
 */
import { cn } from "@/lib/utils";

const PRIORITY_KEYS = [
  "source",
  "extractor",
  "model",
  "pipeline",
  "stage",
  "method",
  "quote_hash",
  "span_id",
  "page",
  "section",
] as const;

function formatValue(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return String(v);
  if (typeof v === "string") return v.length > 48 ? `${v.slice(0, 45)}…` : v;
  if (Array.isArray(v)) return v.length ? `${v.length} items` : "";
  if (typeof v === "object") return "object";
  return String(v);
}

export function ProvenanceStrip({
  provenance,
  className,
}: {
  provenance?: Record<string, unknown> | null;
  className?: string;
}) {
  if (!provenance || typeof provenance !== "object") return null;

  const entries: Array<{ key: string; value: string }> = [];
  const seen = new Set<string>();

  for (const key of PRIORITY_KEYS) {
    if (!(key in provenance)) continue;
    const value = formatValue(provenance[key]);
    if (!value || value === "object") continue;
    entries.push({ key, value });
    seen.add(key);
  }

  for (const [key, raw] of Object.entries(provenance)) {
    if (seen.has(key) || entries.length >= 6) break;
    if (key === "claim_equals_quote") continue;
    const value = formatValue(raw);
    if (!value || value === "object") continue;
    entries.push({ key, value });
  }

  if (entries.length === 0) return null;

  return (
    <div
      className={cn(
        "mt-1.5 space-y-1 rounded border border-border bg-muted/20 px-2 py-1.5",
        className,
      )}
      aria-label="Provenance"
    >
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Provenance
      </p>
      <dl className="grid gap-0.5">
        {entries.map(({ key, value }) => (
          <div key={key} className="flex gap-1.5 text-[10px] leading-snug">
            <dt className="shrink-0 font-medium text-muted-foreground">{key}</dt>
            <dd className="min-w-0 truncate text-foreground/85" title={value}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
