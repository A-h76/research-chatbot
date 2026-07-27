import { useEffect, useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const LOGIN_HREF = "/login";

/**
 * D9 / M11 — Friendly session expiry (replaces silent dump to /login).
 * Listens for `soro:session-expired` from apiClient on 401.
 */
export function SessionExpiredModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onExpired = () => setOpen(true);
    window.addEventListener("soro:session-expired", onExpired);
    return () => window.removeEventListener("soro:session-expired", onExpired);
  }, []);

  function signIn() {
    window.location.href = LOGIN_HREF;
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        // Must sign in — closing without action still sends to login.
        if (!next) signIn();
        else setOpen(true);
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Session expired</AlertDialogTitle>
          <AlertDialogDescription>
            Your sign-in session ended or isn’t valid anymore. Sign in again to keep
            working — open papers and drafts on this device stay where they are.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction onClick={signIn}>Sign in again</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
