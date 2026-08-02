import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { RefreshCw, LogOut } from "lucide-react";
import { Segmented } from "../components/Segmented";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTheme } from "@/context/ThemeContext";
import { useUI } from "@/context/UIContext";
import { useModels, useRefreshModels } from "@/features/models/useModels";
import { useMe, useUpdateInstructions } from "@/features/profile/useMe";
import { toast } from "@/components/common/Toast";
import { SEARCH_MODES } from "@/lib/constants";
import type { SearchMode } from "@/types/api";

function Row({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-b border-border py-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export function AppearanceSection() {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <Row label="Theme" description="Choose light or dark appearance.">
        <Segmented
          value={theme}
          onChange={(v) => setTheme(v)}
          options={[
            { value: "dark", label: "Dark" },
            { value: "light", label: "Light" },
          ]}
        />
      </Row>
    </div>
  );
}

/** Chat assistant defaults — under Advanced in Settings nav. */
export function ChatDefaultsSection() {
  const { defaultSearchMode, setDefaultSearchMode } = useUI();
  return (
    <div>
      <Row label="Default web-search mode" description="Applied to new chats.">
        <Segmented<SearchMode>
          value={defaultSearchMode}
          onChange={setDefaultSearchMode}
          options={SEARCH_MODES.map((m) => ({
            value: m.value,
            label: m.value === "on" ? "Always" : m.value === "auto" ? "Auto" : "Off",
          }))}
        />
      </Row>
    </div>
  );
}

export function ModelsSection() {
  const { data } = useModels();
  const refreshModels = useRefreshModels();
  const { defaultModel, setDefaultModel } = useUI();
  const { data: me } = useMe();
  const [refreshing, setRefreshing] = useState(false);
  const models = data?.models ?? [];
  const current = defaultModel || me?.default_model || models[0] || "";

  return (
    <div>
      <Row label="Default model for new chats" description="The model selected when you start a chat.">
        <Select value={current} onValueChange={(v) => setDefaultModel(v as string)}>
          <SelectTrigger className="w-56">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {models.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Row>
      <Row label="Model list" description="Refreshed automatically from your account.">
        <Button
          variant="outline"
          disabled={refreshing}
          onClick={async () => {
            setRefreshing(true);
            await refreshModels();
            setRefreshing(false);
            toast.success("Model list refreshed");
          }}
        >
          <RefreshCw className={refreshing ? "size-4 animate-spin" : "size-4"} /> Refresh
        </Button>
      </Row>
    </div>
  );
}

export function ApiSection() {
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-5 text-sm text-muted-foreground">
      <p className="font-medium text-foreground">API key</p>
      <p className="mt-1">
        OpenAI API key is stored securely on the backend (via the server's <code>.env</code>) and is never
        exposed to the browser. Model access is derived from your account.
      </p>
    </div>
  );
}

export function PersonalizationSection() {
  const { data: me } = useMe();
  const updateInstructions = useUpdateInstructions();
  const [value, setValue] = useState(me?.custom_instructions ?? "");
  const [newEmail, setNewEmail] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <div className="grid gap-1.5">
          <Label>Custom instructions — applied to every chat</Label>
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. I'm writing a master's thesis on machine learning. Prefer formal tone, APA style."
            className="min-h-32"
          />
        </div>
        <Button
          className="self-end"
          onClick={async () => {
            await updateInstructions.mutateAsync(value);
            toast.success("Saved — applies to all new messages");
          }}
        >
          Save instructions
        </Button>
      </div>

      <div className="rounded-xl border border-border bg-muted/30 p-5">
        <p className="text-sm font-medium text-foreground">Email</p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Current address: <span className="text-foreground">{me?.email}</span>
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1 grid gap-1.5">
            <Label htmlFor="new-email">New email</Label>
            <input
              id="new-email"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-[14px] outline-none focus:ring-2 focus:ring-primary/30"
              placeholder="you@university.edu"
            />
          </div>
          <Button
            variant="outline"
            disabled={emailBusy || !newEmail.trim()}
            onClick={async () => {
              setEmailBusy(true);
              try {
                const { api } = await import("@/lib/apiClient");
                await api.post("/auth/change-email", { new_email: newEmail.trim() });
                toast.success("Check your new inbox to confirm the change");
                setNewEmail("");
              } catch {
                toast.error("Could not start email change");
              } finally {
                setEmailBusy(false);
              }
            }}
          >
            Change email
          </Button>
        </div>
      </div>
    </div>
  );
}

export function MemorySection() {
  const navigate = useNavigate();
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-5 text-sm text-muted-foreground">
      <p className="font-medium text-foreground">Long-term memory</p>
      <p className="mt-1">
        Dhund selectively remembers durable facts about you. You can view, edit importance, and delete
        memories on the Memory page.
      </p>
      <Button variant="outline" className="mt-3" onClick={() => navigate("/memory")}>
        Manage memories
      </Button>
    </div>
  );
}

export function PrivacySection() {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border border-border bg-muted/40 p-5 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">Your data</p>
        <p className="mt-1">
          Conversations, files, citations, and memories are stored in your private database. Nothing is shared
          publicly — this app is login-gated. Export or delete your data under <b>Data controls</b>.
        </p>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
        <Link to="/privacy" className="text-muted-foreground underline hover:text-foreground">Privacy Policy</Link>
        <Link to="/terms" className="text-muted-foreground underline hover:text-foreground">Terms of Service</Link>
        <Link to="/cookies" className="text-muted-foreground underline hover:text-foreground">Cookie Policy</Link>
        <Link to="/support" className="text-muted-foreground underline hover:text-foreground">Contact &amp; Support</Link>
      </div>
      <Button variant="outline" className="self-start" onClick={() => (window.location.href = "/logout")}>
        <LogOut className="size-4" /> Log out
      </Button>
    </div>
  );
}

export function AboutSection() {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border border-border bg-muted/40 p-5 text-sm text-muted-foreground">
        <p className="text-base font-semibold text-foreground">Dhund</p>
        <p className="mt-1">Research Operating System — evidence-backed literature review.</p>
        <p className="mt-3">
          Core path: Library → Evidence decisions → Grounded writing → Verify citations → Export.
          Chat, memory, and RAG support the workflow; they are not the product.
        </p>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
        <Link to="/about" className="text-muted-foreground underline hover:text-foreground">About page</Link>
        <Link to="/support" className="text-muted-foreground underline hover:text-foreground">Contact &amp; Support</Link>
      </div>
    </div>
  );
}
