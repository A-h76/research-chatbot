import { api } from "@/lib/apiClient";

export type LibraryFormat = "bibtex" | "ris";

export interface LibraryConnections {
  zotero: {
    available: boolean;
    connected: boolean;
    username: string;
    external_user_id: string;
    last_synced_at?: string | null;
    incremental_sync?: boolean;
    missing_env?: string[];
  };
  mendeley: {
    available: boolean;
    connected: boolean;
    coming_soon: boolean;
    username: string;
    external_user_id?: string;
    last_synced_at?: string | null;
    incremental_sync?: boolean;
    missing_env?: string[];
  };
  formats: string[];
  adapters?: string[];
}

export interface LibraryImportResult {
  ok?: boolean;
  created: number;
  skipped: number;
  created_ids?: number[];
  skipped_items?: Array<{
    title?: string;
    reason?: string;
    file_id?: number;
    doi?: string;
  }>;
  project_id?: number | null;
  parsed?: number;
  format?: string;
  source?: string;
  error?: string;
  detail?: string;
}

export interface ZoteroCollection {
  key: string;
  name: string;
  parent: string | null;
}

export type MendeleyFolder = ZoteroCollection;

export const libraryBridgeApi = {
  connections: () => api.get<LibraryConnections>("/api/library/connections"),

  importText: (body: {
    format: LibraryFormat;
    content: string;
    project_id?: number | null;
    create_project?: boolean;
    project_name?: string;
  }) => api.post<LibraryImportResult>("/api/library/import", body),

  importFile: async (
    file: File,
    opts: {
      format?: LibraryFormat;
      project_id?: number | null;
      create_project?: boolean;
      project_name?: string;
    } = {},
  ) => {
    const fd = new FormData();
    fd.append("file", file);
    if (opts.format) fd.append("format", opts.format);
    if (opts.project_id != null) fd.append("project_id", String(opts.project_id));
    if (opts.create_project) fd.append("create_project", "true");
    if (opts.project_name) fd.append("project_name", opts.project_name);
    return api.postForm<LibraryImportResult>("/api/library/import", fd);
  },

  exportUrl: (format: LibraryFormat = "bibtex", projectId?: number | null) => {
    const p = new URLSearchParams({ format });
    if (projectId != null) p.set("project_id", String(projectId));
    return `/api/library/export?${p.toString()}`;
  },

  zoteroConnect: () =>
    api.post<{ authorize_url: string }>("/api/library/zotero/connect", {}),

  zoteroDisconnect: () => api.post<{ ok: boolean }>("/api/library/zotero/disconnect", {}),

  zoteroCollections: () =>
    api.get<{ items: ZoteroCollection[] }>("/api/library/zotero/collections"),

  zoteroImport: (body: {
    collection_key?: string;
    project_id?: number | null;
    create_project?: boolean;
    project_name?: string;
    limit?: number;
  }) => api.post<LibraryImportResult>("/api/library/zotero/import", body),

  mendeleyConnect: () =>
    api.post<{ authorize_url: string }>("/api/library/mendeley/connect", {}),

  mendeleyDisconnect: () =>
    api.post<{ ok: boolean }>("/api/library/mendeley/disconnect", {}),

  mendeleyFolders: () =>
    api.get<{ items: MendeleyFolder[] }>("/api/library/mendeley/folders"),

  mendeleyImport: (body: {
    folder_id?: string;
    project_id?: number | null;
    create_project?: boolean;
    project_name?: string;
    limit?: number;
  }) => api.post<LibraryImportResult>("/api/library/mendeley/import", body),

  zoteroSync: (body: { limit?: number } = {}) =>
    api.post<LibrarySyncResult>("/api/library/zotero/sync", body),

  mendeleySync: (body: { limit?: number } = {}) =>
    api.post<LibrarySyncResult>("/api/library/mendeley/sync", body),

  syncRuns: (provider?: string) => {
    const q = provider ? `?provider=${encodeURIComponent(provider)}` : "";
    return api.get<{ items: LibrarySyncRun[] }>(`/api/library/sync/runs${q}`);
  },

  attachPdf: async (fileId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.postForm<{ ok: boolean; file: { id: number }; queued?: boolean }>(
      `/api/library/files/${fileId}/attach`,
      fd,
    );
  },

  health: (projectId?: number | null) => {
    const q =
      projectId != null ? `?project_id=${encodeURIComponent(String(projectId))}` : "";
    return api.get<LibraryHealth>(`/api/library/health${q}`);
  },

  duplicates: (projectId?: number | null, limit = 50) => {
    const p = new URLSearchParams({ limit: String(limit) });
    if (projectId != null) p.set("project_id", String(projectId));
    return api.get<{ items: LibraryDuplicateGroup[]; count: number }>(
      `/api/library/duplicates?${p.toString()}`,
    );
  },

  mergeDuplicates: (body: {
    keep_id: number;
    merge_ids: number[];
    delete_merged?: boolean;
  }) => api.post<LibraryMergeResult>("/api/library/duplicates/merge", body),
};

export interface LibraryHealth {
  total: number;
  by_readiness: {
    metadata_only: number;
    pdf_attached: number;
    analysed: number;
    indexed: number;
    research_ready: number;
  };
  need_pdf: number;
  stub_ratio: number;
  processing: number;
  research_ready: number;
  sync: {
    connections: Array<{
      provider: string;
      last_synced_at: string | null;
      has_cursor: boolean;
    }>;
    runs: Array<{
      id: number;
      provider: string;
      status: string;
      started_at: string | null;
      created: number;
      updated: number;
      conflicts: number;
      error: string;
    }>;
  };
  generated_at: string;
}

export interface LibraryDuplicateGroup {
  reason: string;
  key: string;
  keep_id: number;
  file_ids: number[];
  titles: string[];
  has_pdf: boolean[];
}

export interface LibraryMergeResult {
  ok?: boolean;
  keep_id: number;
  merged_ids: number[];
  skipped?: Array<{ id: number; reason: string }>;
  file?: { id: number };
  error?: string;
}

export interface LibrarySyncResult {
  ok?: boolean;
  created: number;
  updated: number;
  skipped: number;
  conflicts: number;
  fetched?: number;
  sync_run_id?: number;
  last_synced_at?: string;
  provider?: string;
  error?: string;
  detail?: string;
}

export interface LibrarySyncRun {
  id: number;
  provider: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  created: number;
  updated: number;
  skipped: number;
  conflicts: number;
  error: string;
}
