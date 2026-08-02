import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, MailPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { toast } from "@/components/common/Toast";
import { adminOpsApi } from "../api";

export function InvitesPanel() {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [includeUsed, setIncludeUsed] = useState(false);
  const [lastToken, setLastToken] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "ops", "invites", includeUsed],
    queryFn: () => adminOpsApi.listInvites(includeUsed),
  });

  const create = useMutation({
    mutationFn: () => adminOpsApi.createInvite(email.trim(), true),
    onSuccess: (res) => {
      setLastToken(res.token);
      setEmail("");
      qc.invalidateQueries({ queryKey: ["admin", "ops", "invites"] });
      toast.success(
        res.email_sent ? `Invite emailed to ${res.email}` : `Invite created for ${res.email}`,
      );
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Invite failed"),
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-border p-4">
        <p className="text-sm font-medium">Create invite</p>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Closed-beta allowlist entry — emails a signup link when mail is configured.
        </p>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="min-w-[16rem] flex-1 space-y-1">
            <Label htmlFor="invite-email" className="text-xs">
              Email
            </Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="researcher@university.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && email.includes("@")) create.mutate();
              }}
            />
          </div>
          <Button
            size="sm"
            disabled={create.isPending || !email.includes("@")}
            onClick={() => create.mutate()}
          >
            <MailPlus className="size-3.5" />
            Invite
          </Button>
        </div>
        {lastToken && (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
            <span className="text-muted-foreground">Raw token (copy once):</span>
            <code className="max-w-full truncate font-mono">{lastToken}</code>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7"
              onClick={async () => {
                await navigator.clipboard.writeText(lastToken);
                toast.success("Token copied");
              }}
            >
              <Copy className="size-3.5" />
              Copy
            </Button>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">Invites</p>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={includeUsed}
            onChange={(e) => setIncludeUsed(e.target.checked)}
          />
          Include used
        </label>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
          <LoadingSpinner /> Loading invites…
        </div>
      ) : isError ? (
        <p className="text-sm text-destructive">
          Could not load invites.{" "}
          <button type="button" className="underline" onClick={() => refetch()}>
            Retry
          </button>
        </p>
      ) : items.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">No invites yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[32rem] text-left text-[13px]">
            <thead className="border-b border-border bg-muted/30 text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Email</th>
                <th className="px-3 py-2 font-medium">Expires</th>
                <th className="px-3 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((inv) => (
                <tr key={inv.id} className="border-b border-border/60 last:border-0">
                  <td className="px-3 py-2">{inv.email}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {inv.expires_at ? new Date(inv.expires_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {inv.used_at
                      ? "Used"
                      : inv.expired
                        ? "Expired"
                        : "Pending"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
