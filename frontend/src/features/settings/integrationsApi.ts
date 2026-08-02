import { api } from "@/lib/apiClient";

export type IntegrationCapabilityKey =
  | "import"
  | "sync"
  | "pdf_pull"
  | "folder_watch"
  | "write_back";

export type IntegrationAuth = "oauth" | "api_key" | "none" | "file";

export type IntegrationConnectionState =
  | "connected"
  | "not_connected"
  | "coming_soon"
  | "n/a";

export interface IntegrationCategory {
  id: string;
  name: string;
  description: string;
}

export interface IntegrationActionRef {
  method?: string;
  path?: string;
}

export interface IntegrationProvider {
  id: string;
  name: string;
  category: string;
  status: string;
  availability: "live" | "soon" | "not_planned" | string;
  capabilities: Record<IntegrationCapabilityKey, boolean>;
  supported_features: string[];
  auth: IntegrationAuth;
  brand_color?: string;
  logo?: string;
  mark?: string;
  blurb?: string;
  docs_url?: string;
  connection_state: IntegrationConnectionState;
  connection: {
    state: IntegrationConnectionState;
    username?: string;
    last_sync?: string | null;
    items_imported?: number;
  };
  last_sync?: string | null;
  health?: {
    ok: boolean;
    error?: string;
    last_run_status?: string | null;
  };
  actions: {
    connect?: IntegrationActionRef;
    disconnect?: IntegrationActionRef;
    sync?: IntegrationActionRef;
    pull_pdfs?: IntegrationActionRef;
    deep_link?: string;
  };
  connectable?: boolean;
  server_configured?: boolean;
}

export interface IntegrationsCatalog {
  categories: IntegrationCategory[];
  providers: IntegrationProvider[];
}

export const integrationsApi = {
  catalog: () => api.get<IntegrationsCatalog>("/api/integrations/catalog"),

  publicCatalog: () =>
    api.get<IntegrationsCatalog>("/api/integrations/catalog/public"),

  /** Generic action POST/GET using catalog action refs — no provider-specific FE. */
  runAction: async (action: IntegrationActionRef | undefined, body?: object) => {
    if (!action?.path) throw new Error("Action not available");
    const method = (action.method || "POST").toUpperCase();
    if (method === "GET") {
      // OAuth connect — full page navigation
      window.location.href = action.path;
      return null;
    }
    return api.post<Record<string, unknown>>(action.path, body ?? {});
  },
};
