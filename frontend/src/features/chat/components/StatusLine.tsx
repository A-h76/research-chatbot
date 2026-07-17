import { Loader2 } from "lucide-react";

export function StatusLine({ text }: { text: string }) {
  return (
    <div className="mb-1.5 flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-3.5 animate-spin" />
      <span>{text}</span>
    </div>
  );
}
