import { useNavigate } from "react-router-dom";
import { SquarePen } from "lucide-react";
import { Button } from "@/components/ui/button";

export function NewChatButton() {
  const navigate = useNavigate();
  return (
    <Button
      variant="outline"
      className="mx-3 mb-2 justify-start gap-2.5 rounded-xl border-sidebar-border text-sidebar-foreground hover:bg-sidebar-accent"
      onClick={() => navigate("/chat")}
    >
      <SquarePen className="size-4" />
      New chat
    </Button>
  );
}
