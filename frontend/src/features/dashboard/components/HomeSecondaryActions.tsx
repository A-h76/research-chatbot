import { useNavigate } from "react-router-dom";
import { BookOpen, FlaskConical, FolderKanban, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const ACTIONS: {
  title: string;
  subtitle: string;
  href: string;
  icon: LucideIcon;
}[] = [
  {
    title: "Create Literature Review",
    subtitle: "Organize papers → writing",
    href: "/writing?action=lit-review",
    icon: BookOpen,
  },
  {
    title: "Start Research Project",
    subtitle: "Questions, evidence, writing",
    href: "/projects?new=1",
    icon: FlaskConical,
  },
  {
    title: "Explore Library",
    subtitle: "Browse collections and imports",
    href: "/library",
    icon: FolderKanban,
  },
];

export function HomeSecondaryActions({ className }: { className?: string }) {
  const navigate = useNavigate();

  return (
    <div className={cn("grid gap-2", className)}>
      {ACTIONS.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.title}
            type="button"
            onClick={() => navigate(item.href)}
            className={cn(
              "flex w-full items-start gap-3 rounded-md border border-border bg-card px-3.5 py-3 text-left",
              "transition-colors duration-150 ease-out hover:bg-muted/40",
            )}
          >
            <Icon className="mt-0.5 size-3.5 shrink-0 text-foreground/55" aria-hidden />
            <span className="min-w-0">
              <span className="block text-[13px] font-medium text-foreground">{item.title}</span>
              <span className="mt-0.5 block text-[12px] text-foreground/65">{item.subtitle}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
