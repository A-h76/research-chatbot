import { useState } from "react";
import { Sparkles, FlaskConical } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { EmptyState } from "@/components/common/EmptyState";
import { useAiPrompts, useAiTest } from "../useAi";

// ── List Prompts ──────────────────────────────────────────────────────────────
export function PromptsSection() {
  const { data, isLoading, isError } = useAiPrompts();
  const prompts = data?.prompts ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <LoadingSpinner /> Loading prompts…
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">
        Could not load prompts. Try again in a moment.
      </p>
    );
  }

  if (!prompts.length) {
    return (
      <EmptyState
        icon={<Sparkles className="size-8" />}
        title="No prompts seeded yet"
        description="Prompts are seeded by the worker process or python -m backend.ai.seed — once that's run, they'll show up here."
      />
    );
  }

  return (
    <div className="space-y-3">
      {prompts.map((p) => (
        <div key={p.name} className="rounded-xl border border-border p-4">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{p.name}</p>
            <Badge variant="outline">v{p.version}</Badge>
            {p.is_active && (
              <Badge className="bg-accent-soft text-primary">active</Badge>
            )}
          </div>
          <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-words rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">
            {p.template}
          </pre>
        </div>
      ))}
    </div>
  );
}

// ── Test AI (dev-only) ──────────────────────────────────────────────────────────
// Gated by import.meta.env.DEV at the call site (SettingsPage only adds this
// section to the list in a dev build — see that file) — the same pattern
// App.tsx already uses for the React Query devtools. Not a real "admin" role:
// this app has no roles/permissions system anywhere, so "admin-only" here
// means "dev build only," matching the backend's own IS_PRODUCTION gate on
// POST /api/ai/test (it 403s there regardless of what the frontend shows).
export function TestAiSection() {
  const [message, setMessage] = useState("Say hello in one short sentence.");
  const test = useAiTest();

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
        <FlaskConical className="mt-0.5 size-4 shrink-0" />
        <p>
          Dev-only tool — calls a real model and costs real money. The backend
          also refuses this call outside development, independent of this page.
        </p>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="ai-test-message">Test message</Label>
        <Textarea
          id="ai-test-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="min-h-24"
        />
      </div>

      <Button onClick={() => test.mutate({ message })} disabled={test.isPending || !message.trim()}>
        {test.isPending ? "Calling…" : "Send test call"}
      </Button>

      {test.isError && (
        <p className="text-sm text-destructive">
          {test.error instanceof Error ? test.error.message : "Test call failed"}
        </p>
      )}

      {test.data && (
        <div className="space-y-1.5 rounded-xl border border-border bg-muted/40 p-4 text-sm">
          <p className="whitespace-pre-wrap">{test.data.content}</p>
          <p className="text-xs text-muted-foreground">
            {test.data.model} · {test.data.total_tokens} tokens
            {" "}({test.data.prompt_tokens} in / {test.data.completion_tokens} out)
            · ${test.data.cost.toFixed(6)} · {test.data.finish_reason}
          </p>
        </div>
      )}
    </div>
  );
}
