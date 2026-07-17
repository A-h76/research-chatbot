import { Check, Copy, RefreshCw } from "lucide-react";
import { useClipboard } from "@/hooks/useClipboard";

export function MessageActions({
  content,
  onRegenerate,
}: {
  content: string;
  onRegenerate?: () => void;
}) {
  const { copied, copy } = useClipboard();
  return (
    <div className="mt-2 flex items-center gap-0.5">
      <button
        onClick={() => copy(content)}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        title="Copy"
      >
        {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        {copied ? "Copied" : "Copy"}
      </button>
      {onRegenerate && (
        <button
          onClick={onRegenerate}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          title="Regenerate"
        >
          <RefreshCw className="size-3.5" />
          Regenerate
        </button>
      )}
    </div>
  );
}
