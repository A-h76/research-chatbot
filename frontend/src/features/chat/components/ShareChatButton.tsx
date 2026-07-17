import { Share2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useClipboard } from "@/hooks/useClipboard";
import { toast } from "@/components/common/Toast";

export function ShareChatButton() {
  const { copied, copy } = useClipboard();
  return (
    <Button
      variant="ghost"
      size="sm"
      className="gap-1.5 text-muted-foreground"
      onClick={() => {
        copy(window.location.href);
        toast.success("Chat link copied");
      }}
      title="Copy link to this chat"
    >
      {copied ? <Check className="size-4" /> : <Share2 className="size-4" />}
      <span className="hidden sm:inline">Share</span>
    </Button>
  );
}
