import { createBrowserRouter, Navigate } from "react-router-dom";
import { RootLayout }               from "./RootLayout";
import { ChatPage }                 from "@/features/chat/pages/ChatPage";
import { ProjectsPage }             from "@/features/projects/pages/ProjectsPage";
import { ProjectDetailPage }        from "@/features/projects/pages/ProjectDetailPage";
import { FilesPage }                from "@/features/files/pages/FilesPage";
import { CitationsPage }            from "@/features/citations/pages/CitationsPage";
import { MemoryPage }               from "@/features/memory/pages/MemoryPage";
import { NotesPage }                from "@/features/notes/pages/NotesPage";
import { SettingsPage }             from "@/features/settings/pages/SettingsPage";
import { LegalPage }                from "@/features/legal/LegalPage";
import { SupportPage }              from "@/features/support/SupportPage";
import { PaperOverviewPage }        from "@/features/papers/pages/PaperOverviewPage";
import { PaperChatPage }            from "@/features/papers/pages/PaperChatPage";
import { DashboardPage }            from "@/features/dashboard/DashboardPage";
import { MultiPaperAnalysisPage }   from "@/features/analysis/pages/MultiPaperAnalysisPage";
import { SearchPage }               from "@/features/search/pages/SearchPage";
import { WritingPage }              from "@/features/writing/pages/WritingPage";

export const router = createBrowserRouter([
  { path: "/privacy",  element: <LegalPage slug="privacy" /> },
  { path: "/terms",    element: <LegalPage slug="terms" /> },
  { path: "/cookies",  element: <LegalPage slug="cookies" /> },
  { path: "/about",    element: <LegalPage slug="about" /> },
  { path: "/support",  element: <SupportPage /> },
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true,                                   element: <DashboardPage /> },
      { path: "chat",                                  element: <ChatPage /> },
      { path: "c/:conversationId",                     element: <ChatPage /> },
      { path: "projects",                              element: <ProjectsPage /> },
      { path: "projects/:projectId",                   element: <ProjectDetailPage /> },
      { path: "files",                                 element: <FilesPage /> },
      { path: "papers/:fileId",                        element: <PaperOverviewPage /> },
      { path: "papers/:fileId/chat",                   element: <PaperChatPage /> },
      { path: "papers/:fileId/chat/:conversationId",   element: <PaperChatPage /> },
      { path: "analysis/compare",                      element: <MultiPaperAnalysisPage /> },
      { path: "citations",                             element: <CitationsPage /> },
      { path: "notes",                                 element: <NotesPage /> },
      { path: "memory",                                element: <MemoryPage /> },
      { path: "search",                                element: <SearchPage /> },
      { path: "writing",                               element: <WritingPage /> },
      { path: "settings",                              element: <SettingsPage /> },
      { path: "settings/:section",                     element: <SettingsPage /> },
      { path: "*",                                     element: <Navigate to="/" replace /> },
    ],
  },
]);
