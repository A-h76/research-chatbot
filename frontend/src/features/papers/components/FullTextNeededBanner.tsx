import { useRef, useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, RefreshCw, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { FullTextResolution } from "@/types/api";

type Props = {
  fulltext?: FullTextResolution | null;
  sourceUrl?: string;
  doi?: string;
  busy?: boolean;
  onRetry: () => void;
  onAttach: (file: File) => void;
};

/**
 * Soft UFTR banner — no engineering jargon by default; Details expands outcomes.
 */
export function FullTextNeededBanner({
  fulltext,
  sourceUrl,
  doi,
  busy,
  onRetry,
  onAttach,
}: Props) {
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const publisher =
    (sourceUrl || "").trim() ||
    (doi ? `https://doi.org/${doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "")}` : "");

  const reason =
    fulltext?.user_reason ||
    "Couldn't access the publisher's full text automatically.";

  return (
    <div
      className="rounded-lg border border-amber-200/80 bg-amber-50/60 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-950/30"
      role="status"
    >
      <p className="text-[13px] font-medium text-foreground">Full text unavailable</p>
      <p className="mt-0.5 text-[12px] text-muted-foreground">
        Metadata imported successfully. {reason}
      </p>
      {!open && fulltext?.outcome ? (
        <p className="mt-1 text-[12px] text-muted-foreground">
          Reason:{" "}
          <span className="text-foreground/80">
            {fulltext.outcome === "BOT_PROTECTION" ||
            fulltext.outcome === "PUBLISHER_PAYWALL"
              ? "Publisher restrictions"
              : reason}
          </span>
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={onRetry}
          className="h-8 gap-1.5 text-[12px]"
        >
          <RefreshCw className={cn("size-3.5", busy && "animate-spin")} />
          Retry Full Text
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="h-8 gap-1.5 text-[12px]"
        >
          <Upload className="size-3.5" />
          Attach PDF
        </Button>
        {publisher ? (
          <a
            href={publisher}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-[12px] text-muted-foreground hover:text-foreground"
          >
            Open Publisher <ExternalLink className="size-3" />
          </a>
        ) : null}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex h-8 items-center gap-1 px-1 text-[12px] text-muted-foreground hover:text-foreground"
        >
          Details {open ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </button>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onAttach(f);
          e.target.value = "";
        }}
      />

      {open ? (
        <div className="mt-3 space-y-1.5 border-t border-border/60 pt-2 font-mono text-[11px] text-muted-foreground">
          <p>
            outcome: <span className="text-foreground/80">{fulltext?.outcome || "—"}</span>
          </p>
          {fulltext?.full_text_source ? (
            <p>
              source: <span className="text-foreground/80">{fulltext.full_text_source}</span>
            </p>
          ) : null}
          {fulltext?.last_attempt_at ? (
            <p>
              last attempt:{" "}
              <span className="text-foreground/80">{fulltext.last_attempt_at}</span>
            </p>
          ) : null}
          {(fulltext?.attempts || []).length > 0 ? (
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              {fulltext!.attempts!.slice(-8).map((a, i) => (
                <li key={`${a.resolver}-${a.at}-${i}`}>
                  {a.resolver}: {a.outcome}
                  {a.reason ? ` (${a.reason})` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p>No resolver attempts recorded yet.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
