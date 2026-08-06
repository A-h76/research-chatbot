import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";

/**
 * Shared paper-tab empty surface (Sprint 4).
 * Keeps titles stable for tests; improves why + next action copy.
 */
export function PaperPhaseEmpty({
  icon,
  title,
  waiting,
  waitingDescription,
  idleDescription,
  onOpenOverview,
}: {
  icon: ReactNode;
  title: string;
  waiting: boolean;
  waitingDescription: string;
  idleDescription: string;
  onOpenOverview?: () => void;
}) {
  return (
    <EmptyState
      icon={icon}
      title={title}
      pending={waiting}
      description={waiting ? waitingDescription : idleDescription}
      action={
        !waiting && onOpenOverview ? (
          <Button type="button" size="sm" variant="outline" onClick={onOpenOverview}>
            Open Overview
          </Button>
        ) : waiting ? (
          <p className="text-[11px] text-muted-foreground">
            Next · Stay on this tab — it updates when the stage finishes.
          </p>
        ) : undefined
      }
    />
  );
}
