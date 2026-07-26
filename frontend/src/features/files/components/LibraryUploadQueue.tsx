import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AiStateBadge, aiStateFromUploadStatus } from "@/features/pipeline";
import type { LibraryUploadItem } from "../hooks/useLibraryUpload";

export function LibraryUploadQueue({
  items,
  onClearFinished,
}: {
  items: LibraryUploadItem[];
  onClearFinished?: () => void;
}) {
  const navigate = useNavigate();
  if (items.length === 0) return null;

  const hasFinished = items.some((i) => i.status !== "uploading");

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Upload queue
        </p>
        {hasFinished && onClearFinished && (
          <Button type="button" variant="ghost" size="sm" className="h-7 gap-1 text-xs" onClick={onClearFinished}>
            <X className="size-3" />
            Clear finished
          </Button>
        )}
      </div>
      <ul className="divide-y divide-border">
        {items.map((item) => (
          <li key={item.key} className="flex items-start gap-3 px-4 py-2.5 text-sm">
            <div className="min-w-0 flex-1">
              {item.status === "uploaded" && item.fileId != null ? (
                <button
                  type="button"
                  className="block w-full truncate text-left font-medium hover:text-primary hover:underline"
                  onClick={() => navigate(`/papers/${item.fileId}`)}
                >
                  {item.filename}
                </button>
              ) : (
                <p className="truncate font-medium">{item.filename}</p>
              )}
              {item.error && (
                <p className="mt-0.5 text-xs text-sem-error">{item.error}</p>
              )}
            </div>
            <AiStateBadge state={aiStateFromUploadStatus(item.status)} />
          </li>
        ))}
      </ul>
    </div>
  );
}
