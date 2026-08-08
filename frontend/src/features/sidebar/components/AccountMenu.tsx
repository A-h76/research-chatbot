import { useNavigate } from "react-router-dom";
import {
  Settings,
  LogOut,
  ChevronsUpDown,
  LifeBuoy,
  Plug,
  Shield,
  BookOpen,
} from "lucide-react";
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

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 1).toUpperCase();
  return `${parts[0]!.slice(0, 1)}${parts[parts.length - 1]!.slice(0, 1)}`.toUpperCase();
}

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
          "flex h-9 w-full items-center gap-2 rounded-[6px] pl-2.5 text-left transition-colors",
          "hover:bg-sidebar-foreground/[0.04] focus-visible:bg-sidebar-foreground/[0.04] focus-visible:outline-none",
          compact ? "pr-1" : "pr-2",
        )}
        title={me.name}
      >
        <Avatar
          size="sm"
          className="after:border-sidebar-foreground/10 dark:after:mix-blend-normal"
        >
          {me.picture ? <AvatarImage src={me.picture} alt={me.name} /> : null}
          <AvatarFallback className="bg-sidebar-foreground/[0.08] text-[10px] font-medium tracking-wide text-sidebar-foreground/55">
            {initials(me.name)}
          </AvatarFallback>
        </Avatar>
        {!compact && (
          <>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12.5px] font-normal leading-tight text-sidebar-foreground/70">
                {me.name}
              </p>
              <p className="mt-0.5 truncate text-[10px] font-normal leading-none text-sidebar-foreground/28">
                Free
              </p>
            </div>
            <ChevronsUpDown className="size-3 shrink-0 text-sidebar-foreground/25" strokeWidth={1.5} />
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
        <DropdownMenuItem onClick={() => navigate("/docs")}>
          <BookOpen /> Docs
        </DropdownMenuItem>
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
