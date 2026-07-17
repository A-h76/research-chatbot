import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const KEY = "cookie-consent";

/** Records the visitor's choice; essential cookies are always required. */
function setConsent(value: "all" | "essential") {
  try {
    localStorage.setItem(KEY, JSON.stringify({ value, at: Date.now() }));
  } catch { /* storage disabled */ }
}

export function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(KEY)) setVisible(true);
    } catch { /* storage disabled — don't nag */ }
  }, []);

  if (!visible) return null;

  const choose = (v: "all" | "essential") => {
    setConsent(v);
    setVisible(false);
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-60 p-3 sm:p-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-lg sm:flex-row sm:items-center">
        <p className="text-sm text-muted-foreground">
          We use an essential cookie to keep you signed in and local storage for preferences. We don't use tracking or ads.{" "}
          <a href="/cookies" className="underline hover:text-foreground">Learn more</a>.
        </p>
        <div className="flex shrink-0 gap-2 sm:ml-auto">
          <Button variant="outline" size="sm" onClick={() => choose("essential")}>
            Essential only
          </Button>
          <Button size="sm" onClick={() => choose("all")}>
            Accept all
          </Button>
        </div>
      </div>
    </div>
  );
}
