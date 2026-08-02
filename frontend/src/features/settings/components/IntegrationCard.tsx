import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ExternalLink, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import {
  integrationsApi,
  type IntegrationCapabilityKey,
  type IntegrationProvider,
} from "../integrationsApi";

const CAP_LABELS: Record<IntegrationCapabilityKey, string> = {
  import: "Import",
  sync: "Sync",
  pdf_pull: "PDF Pull",
  folder_watch: "Folder Watch",
  write_back: "Write Back",
};

const AUTH_LABELS = {
  oauth: "OAuth",
  api_key: "API Key",
  none: "None",
  file: "File",
} as const;

function formatSync(iso: string | null | undefined): string {
  if (!iso) return "Never";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * One reusable Integration Card — no Zotero/Mendeley-specific UI.
 * Future providers appear by registering in the backend catalog.
 */
export function IntegrationCard({
  provider,
  onChanged,
}: {
  provider: IntegrationProvider;
  onChanged?: () => void;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<string | null>(null);
  const caps = (Object.keys(CAP_LABELS) as IntegrationCapabilityKey[]).filter(
    (k) => provider.capabilities?.[k],
  );
  const state = provider.connection_state;
  const isSoon = state === "coming_soon" || provider.availability !== "live";
  const canConnect = Boolean(provider.connectable && provider.actions.connect && !isSoon);
  const canDisconnect = Boolean(
    provider.connectable && state === "connected" && provider.actions.disconnect,
  );
  const canSync = Boolean(state === "connected" && provider.actions.sync);
  const canPull = Boolean(state === "connected" && provider.actions.pull_pdfs);
  const deepLink = provider.actions.deep_link;

  const run = async (key: string, action: Parameters<typeof integrationsApi.runAction>[0], body?: object) => {
    setBusy(key);
    try {
      const res = await integrationsApi.runAction(action, body);
      if (res == null) return; // navigated (OAuth)
      if (key === "sync" && res.status === "queued" && res.sync_run_id != null) {
        toast.success(`${provider.name} sync queued`);
      } else if (key === "pull") {
        toast.success(`Pulled ${Number(res.pulled ?? 0)} PDF(s)`);
      } else if (key === "disconnect") {
        toast.success(`${provider.name} disconnected`);
      } else {
        toast.success(`${provider.name} updated`);
      }
      onChanged?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <article
      className={cn(
        "rounded-xl border border-border/80 bg-card/40 p-4",
        isSoon && "opacity-90",
      )}
      style={{ ["--brand" as string]: provider.brand_color || "#0F6E6A" }}
    >
      <div className="flex items-start gap-3">
        <div
          className="flex size-10 shrink-0 items-center justify-center rounded-lg text-[11px] font-semibold text-white"
          style={{ background: "var(--brand)" }}
          aria-hidden
        >
          {provider.logo ? (
            <img
              src={`/static/${provider.logo}`}
              alt=""
              className="size-6 object-contain"
              width={24}
              height={24}
            />
          ) : (
            provider.mark || provider.name.slice(0, 2).toUpperCase()
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">{provider.name}</h3>
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-[10px] font-medium",
                state === "connected" && "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
                state === "not_connected" && "bg-muted text-muted-foreground",
                state === "coming_soon" && "bg-amber-500/15 text-amber-800 dark:text-amber-300",
                state === "n/a" && "bg-muted text-muted-foreground",
              )}
            >
              {provider.status}
            </span>
          </div>
          {provider.blurb ? (
            <p className="mt-1 text-[12px] text-muted-foreground">{provider.blurb}</p>
          ) : null}
        </div>
      </div>

      <dl className="mt-3 grid gap-1.5 text-[11px] text-muted-foreground sm:grid-cols-2">
        <div>
          <dt className="font-medium text-foreground/80">Authentication</dt>
          <dd>{AUTH_LABELS[provider.auth] ?? provider.auth}</dd>
        </div>
        <div>
          <dt className="font-medium text-foreground/80">Last sync</dt>
          <dd>{formatSync(provider.last_sync ?? provider.connection?.last_sync)}</dd>
        </div>
        <div>
          <dt className="font-medium text-foreground/80">Items imported</dt>
          <dd>{provider.connection?.items_imported ?? 0}</dd>
        </div>
        <div>
          <dt className="font-medium text-foreground/80">Capabilities</dt>
          <dd>
            {caps.length
              ? caps.map((c) => CAP_LABELS[c]).join(" · ")
              : "—"}
          </dd>
        </div>
      </dl>

      {provider.health && !provider.health.ok && provider.health.error ? (
        <p className="mt-2 rounded-md bg-destructive/10 px-2 py-1.5 text-[11px] text-destructive">
          {provider.health.error}
        </p>
      ) : null}

      {provider.connection?.username ? (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Account: {provider.connection.username}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-1.5">
        {canConnect && state !== "connected" ? (
          <Button
            size="sm"
            className="h-7 text-[11px]"
            disabled={busy != null}
            onClick={() => void run("connect", provider.actions.connect)}
          >
            {busy === "connect" ? <Loader2 className="size-3 animate-spin" /> : null}
            Connect
          </Button>
        ) : null}
        {canSync ? (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[11px]"
            disabled={busy != null}
            onClick={() => void run("sync", provider.actions.sync, {})}
          >
            {busy === "sync" ? <Loader2 className="size-3 animate-spin" /> : null}
            Sync Now
          </Button>
        ) : null}
        {canPull ? (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[11px]"
            disabled={busy != null}
            onClick={() => void run("pull", provider.actions.pull_pdfs, { limit: 20 })}
          >
            {busy === "pull" ? <Loader2 className="size-3 animate-spin" /> : null}
            Pull PDFs
          </Button>
        ) : null}
        {canDisconnect ? (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-[11px] text-muted-foreground"
            disabled={busy != null}
            onClick={() => void run("disconnect", provider.actions.disconnect)}
          >
            Disconnect
          </Button>
        ) : null}
        {deepLink ? (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-[11px]"
            onClick={() => {
              if (deepLink.startsWith("http")) window.open(deepLink, "_blank");
              else navigate(deepLink);
            }}
          >
            Settings
          </Button>
        ) : null}
        {provider.docs_url ? (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 gap-1 text-[11px]"
            onClick={() => window.open(provider.docs_url, "_blank", "noopener,noreferrer")}
          >
            Docs <ExternalLink className="size-3" />
          </Button>
        ) : null}
      </div>
    </article>
  );
}
