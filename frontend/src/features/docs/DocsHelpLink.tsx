import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Settings / in-app help → Mintlify docs (Design Language: docs answer “How does this work?”).
 */
export function DocsHelpLink({
  to = "/docs/overview",
  label = "Open docs",
  hint,
  className,
}: {
  to?: string;
  label?: string;
  hint?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-border bg-muted/20 px-3 py-2 text-[12px]",
        className,
      )}
    >
      <BookOpen className="size-3.5 shrink-0 text-primary" aria-hidden />
      {hint ? <span className="text-muted-foreground">{hint}</span> : null}
      <Link
        to={to}
        className="font-medium text-primary underline-offset-2 hover:underline"
      >
        {label}
      </Link>
    </div>
  );
}
