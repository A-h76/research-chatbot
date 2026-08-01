import { MessageSquare } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

/** Persistent Ask Dhund entry — Cursor-style FAB, not sidebar nav. */
export function AskDhundFab() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const onChat =
    pathname.startsWith("/chat") ||
    pathname.startsWith("/c/") ||
    (pathname.startsWith("/papers/") && pathname.includes("/chat"));

  if (onChat) return null;

  return (
    <button
      type="button"
      onClick={() => navigate("/chat")}
      className={cn(
        "fixed right-5 bottom-5 z-40 flex items-center gap-2 rounded-full border border-border",
        "bg-card px-3.5 py-2.5 text-[13px] font-medium text-foreground shadow-lg",
        "transition-colors hover:bg-muted",
      )}
      title="Ask Dhund"
    >
      <MessageSquare className="size-4 text-primary" />
      Ask Dhund
    </button>
  );
}
