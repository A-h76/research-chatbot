import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import type { Me } from "@/types/api";

const DISMISS_KEY = "dhund-beta-banner-dismissed";

export function BetaBanner({ me }: { me: Me }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!me.beta_mode) return;
    try {
      if (!localStorage.getItem(DISMISS_KEY)) setVisible(true);
    } catch {
      setVisible(true);
    }
  }, [me.beta_mode]);

  if (!visible) return null;

  const dismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* storage disabled */
    }
    setVisible(false);
  };

  return (
    <div className="relative border-b border-primary/20 bg-accent-soft/60 px-4 py-2 text-center text-xs text-muted-foreground sm:text-[13px]">
      <span>
        You&apos;re in the Dhund closed beta — your feedback shapes what we ship next.{" "}
        <Link to="/support?category=beta" className="font-medium text-primary hover:underline">
          Send feedback
        </Link>
      </span>
      <button
        type="button"
        onClick={dismiss}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        aria-label="Dismiss beta banner"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}
