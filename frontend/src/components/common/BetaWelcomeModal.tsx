import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Me } from "@/types/api";

const SEEN_KEY = "dhund-beta-welcome-seen";

const STEPS = [
  "Open Library — import from Zotero, Mendeley, BibTeX/RIS, or upload PDFs",
  "Attach PDFs to metadata-only rows until papers become Research Ready",
  "Compare a few ready papers — then tell us if you’d want to write the review here",
];

export function BetaWelcomeModal({ me }: { me: Me }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!me.beta_mode) return;
    try {
      if (!localStorage.getItem(SEEN_KEY)) setOpen(true);
    } catch {
      setOpen(true);
    }
  }, [me.beta_mode]);

  const close = () => {
    try {
      localStorage.setItem(SEEN_KEY, "1");
    } catch {
      /* storage disabled */
    }
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && close()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mb-1 flex size-10 items-center justify-center rounded-xl border border-border bg-muted">
            <Sparkles className="size-5 text-primary" />
          </div>
          <DialogTitle>Welcome to the Dhund closed beta</DialogTitle>
          <DialogDescription>
            This is an early research workspace. For this beta we&apos;re validating the
            literature-review path — Library → Research Ready → Compare — before building
            a full Writing Studio.
          </DialogDescription>
        </DialogHeader>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
          {STEPS.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <DialogFooter className="flex-col gap-2 sm:flex-col">
          <Button className="w-full" onClick={close}>
            Get started
          </Button>
          <Link
            to="/support"
            onClick={close}
            className="inline-flex h-8 w-full items-center justify-center rounded-lg text-sm text-muted-foreground hover:text-foreground"
          >
            Questions or feedback?
          </Link>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
