import { useNavigate } from "react-router-dom";
import { Settings, LogOut, ChevronsUpDown, LifeBuoy, Plug, Shield } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

export function AccountMenu({
  me,
  compact = false,
}: {
  me: Me;
  compact?: boolean;
}) {
  const navigate = useNavigate();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg py-2 pl-3 text-left transition-colors hover:bg-sidebar-accent",
          compact ? "pr-1" : "pr-2",
        )}
        title={me.name}
      >
        <Avatar>
          {me.picture && <AvatarImage src={me.picture} alt={me.name} />}
          <AvatarFallback>{me.name.slice(0, 1).toUpperCase()}</AvatarFallback>
        </Avatar>
        {!compact && (
          <>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-sidebar-foreground">
                {me.name}
              </p>
              <p className="truncate text-xs text-muted-foreground">Free</p>
            </div>
            <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
          </>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <p className="truncate text-sm font-medium">{me.name}</p>
          <p className="truncate text-xs text-muted-foreground">{me.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate("/settings/integrations")}>
          <Plug /> Integrations
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => navigate("/settings")}>
          <Settings /> Settings
        </DropdownMenuItem>
        {me.is_admin && (
          <DropdownMenuItem onClick={() => navigate("/admin")}>
            <Shield /> Admin
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={() => navigate("/support")}>
          <LifeBuoy /> Help &amp; support
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => (window.location.href = "/logout")}>
          <LogOut /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
