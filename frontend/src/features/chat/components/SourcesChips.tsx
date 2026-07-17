import { ExternalLink } from "lucide-react";
import type { Source } from "@/types/api";

export function SourcesChips({ sources }: { sources: Source[] }) {
  const withUrls = sources.filter((s) => s.url).slice(0, 6);
  if (!withUrls.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {withUrls.map((s, i) => (
        <a
          key={i}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex max-w-[220px] items-center gap-1 truncate rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-muted-foreground hover:text-foreground"
        >
          <ExternalLink className="size-3 shrink-0" />
          <span className="truncate">{s.title || s.url}</span>
        </a>
      ))}
    </div>
  );
}
