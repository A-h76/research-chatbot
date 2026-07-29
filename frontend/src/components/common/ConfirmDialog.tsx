/**
 * Calm confirmation dialog — denser Vengence-style craft, no glow.
 * Prefer for deletes / irreversible research actions.
 */
import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  entityName,
  consequence,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  /** Highlighted subject (paper title, project name, …) */
  entityName?: string | null;
  /** Short irreversible-consequence line under the description */
  consequence?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void | Promise<void>;
}) {
  const [busy, setBusy] = useState(false);

  async function handleConfirm() {
    if (busy) return;
    setBusy(true);
    try {
      await Promise.resolve(onConfirm());
      onOpenChange(false);
    } catch {
      // Keep dialog open so the user can retry or cancel
    } finally {
      setBusy(false);
    }
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        if (busy) return;
        onOpenChange(next);
      }}
    >
      <AlertDialogContent
        size="default"
        className={cn(
          "gap-0 rounded-lg p-0 ring-1 ring-border sm:max-w-[380px]",
          "data-open:zoom-in-100 data-closed:zoom-out-100",
          destructive && "border border-destructive/25",
        )}
      >
        <AlertDialogHeader className="place-items-start gap-0 px-4 pt-4 text-left sm:place-items-start sm:text-left">
          <div className="flex w-full items-start gap-3">
            {destructive ? (
              <span
                className="mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-destructive/10 text-destructive"
                aria-hidden
              >
                <AlertTriangle className="size-4" />
              </span>
            ) : null}
            <div className="min-w-0 flex-1 space-y-1.5">
              <AlertDialogTitle className="text-[15px] font-semibold tracking-tight">
                {title}
              </AlertDialogTitle>
              {entityName ? (
                <p className="truncate rounded-md border border-border bg-muted/40 px-2 py-1.5 text-[12px] font-medium text-foreground">
                  {entityName}
                </p>
              ) : null}
              {description ? (
                <AlertDialogDescription className="text-[13px] leading-relaxed">
                  {description}
                </AlertDialogDescription>
              ) : null}
              {consequence ? (
                <p className="text-[12px] leading-snug text-muted-foreground">{consequence}</p>
              ) : null}
            </div>
          </div>
        </AlertDialogHeader>

        <AlertDialogFooter className="mt-4 rounded-b-lg border-t border-border bg-muted/30 px-4 py-3 sm:justify-end">
          <AlertDialogCancel disabled={busy} size="sm" className="h-8">
            {cancelLabel}
          </AlertDialogCancel>
          <Button
            type="button"
            size="sm"
            variant={destructive ? "destructive" : "default"}
            className="h-8 min-w-[5.5rem]"
            disabled={busy}
            onClick={() => void handleConfirm()}
          >
            {busy ? (
              <>
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
                Working…
              </>
            ) : (
              confirmLabel
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
