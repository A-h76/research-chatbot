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
    file_import?: boolean;
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
    file_import?: boolean;
    missing_env?: string[];
  };
  google_drive?: {
    available: boolean;
    connected: boolean;
    coming_soon?: boolean;
    username: string;
    external_user_id?: string;
    last_synced_at?: string | null;
    incremental_sync?: boolean;
    file_import?: boolean;
    missing_env?: string[];
  };
  dropbox?: {
    available: boolean;
    connected: boolean;
    coming_soon?: boolean;
    username: string;
    external_user_id?: string;
    last_synced_at?: string | null;
    incremental_sync?: boolean;
    file_import?: boolean;
    missing_env?: string[];
  };
  onedrive?: {
    available: boolean;
    connected: boolean;
    coming_soon?: boolean;
    username: string;
    external_user_id?: string;
    last_synced_at?: string | null;
    incremental_sync?: boolean;
    file_import?: boolean;
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

export interface DrivePdfFile {
  id: string;
  name: string;
  mime_type: string;
  size: number;
  modified_time: string;
  web_view_link: string;
}

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

  zoteroSync: (body: { limit?: number; sync?: boolean } = {}) =>
    api.post<LibrarySyncResult>("/api/library/zotero/sync", body),

  mendeleySync: (body: { limit?: number; sync?: boolean } = {}) =>
    api.post<LibrarySyncResult>("/api/library/mendeley/sync", body),

  syncRuns: (provider?: string) => {
    const q = provider ? `?provider=${encodeURIComponent(provider)}` : "";
    return api.get<{ items: LibrarySyncRun[] }>(`/api/library/sync/runs${q}`);
  },

  syncRun: (runId: number) =>
    api.get<LibrarySyncRun>(`/api/library/sync/runs/${runId}`),

  attachPdf: async (fileId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.postForm<{ ok: boolean; file: { id: number }; queued?: boolean }>(
      `/api/library/files/${fileId}/attach`,
      fd,
    );
  },

  pullPdf: (fileId: number) =>
    api.post<LibraryPullPdfsResult>(`/api/library/files/${fileId}/pull-pdf`, {}),

  pullZoteroPdfs: (body: { file_ids?: number[]; limit?: number } = {}) =>
    api.post<LibraryPullPdfsResult>("/api/library/zotero/pull-pdfs", body),

  pullMendeleyPdfs: (body: { file_ids?: number[]; limit?: number } = {}) =>
    api.post<LibraryPullPdfsResult>("/api/library/mendeley/pull-pdfs", body),

  googleDriveConnect: () =>
    api.post<{ authorize_url: string }>("/api/library/google_drive/connect", {}),

  googleDriveDisconnect: () =>
    api.post<{ ok: boolean }>("/api/library/google_drive/disconnect", {}),

  googleDriveFolders: (parentId = "root") =>
    api.get<{ items: MendeleyFolder[]; parent_id: string }>(
      `/api/library/google_drive/folders?parent_id=${encodeURIComponent(parentId)}`,
    ),

  googleDriveFiles: (opts: { folder_id?: string; limit?: number; page_token?: string } = {}) => {
    const p = new URLSearchParams();
    if (opts.folder_id) p.set("folder_id", opts.folder_id);
    if (opts.limit != null) p.set("limit", String(opts.limit));
    if (opts.page_token) p.set("page_token", opts.page_token);
    const q = p.toString();
    return api.get<{
      items: DrivePdfFile[];
      next_page_token: string;
      folder_id: string;
    }>(`/api/library/google_drive/files${q ? `?${q}` : ""}`);
  },

  googleDriveImport: (body: {
    file_ids: string[];
    project_id?: number | null;
    folder_id?: string;
  }) =>
    api.post<LibraryImportResult & { queued?: number; analysis_queued?: boolean }>(
      "/api/library/google_drive/import",
      body,
    ),

  dropboxConnect: () =>
    api.post<{ authorize_url: string }>("/api/library/dropbox/connect", {}),

  dropboxDisconnect: () =>
    api.post<{ ok: boolean }>("/api/library/dropbox/disconnect", {}),

  dropboxFolders: (parentId = "") =>
    api.get<{ items: MendeleyFolder[]; parent_id: string }>(
      `/api/library/dropbox/folders?parent_id=${encodeURIComponent(parentId)}`,
    ),

  dropboxFiles: (opts: { folder_id?: string; limit?: number; page_token?: string } = {}) => {
    const p = new URLSearchParams();
    if (opts.folder_id) p.set("folder_id", opts.folder_id);
    if (opts.limit != null) p.set("limit", String(opts.limit));
    if (opts.page_token) p.set("page_token", opts.page_token);
    const q = p.toString();
    return api.get<{
      items: DrivePdfFile[];
      next_page_token: string;
      folder_id: string;
    }>(`/api/library/dropbox/files${q ? `?${q}` : ""}`);
  },

  dropboxImport: (body: {
    file_ids: string[];
    project_id?: number | null;
    folder_id?: string;
  }) =>
    api.post<LibraryImportResult & { queued?: number; analysis_queued?: boolean }>(
      "/api/library/dropbox/import",
      body,
    ),

  onedriveConnect: () =>
    api.post<{ authorize_url: string }>("/api/library/onedrive/connect", {}),

  onedriveDisconnect: () =>
    api.post<{ ok: boolean }>("/api/library/onedrive/disconnect", {}),

  onedriveFolders: (parentId = "root") =>
    api.get<{ items: MendeleyFolder[]; parent_id: string }>(
      `/api/library/onedrive/folders?parent_id=${encodeURIComponent(parentId)}`,
    ),

  onedriveFiles: (opts: { folder_id?: string; limit?: number; page_token?: string } = {}) => {
    const p = new URLSearchParams();
    if (opts.folder_id) p.set("folder_id", opts.folder_id);
    if (opts.limit != null) p.set("limit", String(opts.limit));
    if (opts.page_token) p.set("page_token", opts.page_token);
    const q = p.toString();
    return api.get<{
      items: DrivePdfFile[];
      next_page_token: string;
      folder_id: string;
    }>(`/api/library/onedrive/files${q ? `?${q}` : ""}`);
  },

  onedriveImport: (body: {
    file_ids: string[];
    project_id?: number | null;
    folder_id?: string;
  }) =>
    api.post<LibraryImportResult & { queued?: number; analysis_queued?: boolean }>(
      "/api/library/onedrive/import",
      body,
    ),

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
  status?: string;
  created?: number;
  updated?: number;
  skipped?: number;
  conflicts?: number;
  fetched?: number;
  sync_run_id?: number;
  job_id?: number;
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
  job_id?: number | null;
}

export interface LibraryPullPdfsResult {
  ok?: boolean;
  provider?: string;
  pulled?: number;
  queued?: number;
  considered?: number;
  skipped?: Array<{ external_id?: string; reason?: string }>;
  errors?: Array<{ external_id?: string; error?: string; file_id?: number }>;
  results?: Array<{ ok?: boolean; file_id?: number; queued?: boolean }>;
  detail?: string;
  error?: string;
}
