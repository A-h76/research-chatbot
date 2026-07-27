import { api } from "@/lib/apiClient";

export type LibraryFormat = "bibtex" | "ris";

export interface LibraryConnections {
  zotero: {
    available: boolean;
    connected: boolean;
    username: string;
    external_user_id: string;
  };
  mendeley: {
    available: boolean;
    connected: boolean;
    coming_soon: boolean;
    username: string;
  };
  formats: string[];
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
};
