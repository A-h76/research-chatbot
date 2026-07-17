import { api } from "@/lib/apiClient";

export interface DashboardPaperBrief {
  id: number;
  name: string;
  title: string;
  authors: string;
  year: string;
  reading_status: "unread" | "reading" | "read";
  meta_status: string;
  created_at: string | null;
}

export interface DashboardChat {
  id: number;
  title: string;
  updated_at: string | null;
  file_id: number | null;
  project_id: number | null;
}

export interface DashboardCitation {
  id: number;
  title: string;
  authors: string;
  year: string;
}

export interface DashboardProject {
  id: number;
  name: string;
  emoji: string;
  paper_count: number;
  chat_count: number;
}

export interface DashboardData {
  library: {
    total_papers: number;
    unread: number;
    reading: number;
    read: number;
    top_tags: { tag: string; count: number }[];
  };
  recent_papers: DashboardPaperBrief[];
  current_papers: DashboardPaperBrief[];
  recent_chats: DashboardChat[];
  recent_citations: DashboardCitation[];
  projects: DashboardProject[];
}

export const dashboardApi = {
  get: () => api.get<DashboardData>("/api/dashboard"),
};
