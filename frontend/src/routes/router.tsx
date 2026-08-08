import { createBrowserRouter, Navigate } from "react-router-dom";
import { RootLayout }               from "./RootLayout";
import { RedirectPreserveSearch }   from "./RedirectPreserveSearch";
import { RouteErrorFallback }       from "@/components/common/RouteErrorFallback";
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
import { DocsPage }                 from "@/features/docs/DocsPage";
import { PaperOverviewPage }        from "@/features/papers/pages/PaperOverviewPage";
import { PaperChatPage }            from "@/features/papers/pages/PaperChatPage";
import { DashboardPage }            from "@/features/dashboard/DashboardPage";
import { MultiPaperAnalysisPage }   from "@/features/analysis/pages/MultiPaperAnalysisPage";
import { SearchPage }               from "@/features/search/pages/SearchPage";
import { WritingWorkspacePage }     from "@/features/writing/pages/WritingWorkspacePage";
import { ProjectWritingRedirect }   from "@/features/writing/pages/ProjectWritingRedirect";
import { AdminPage }                from "@/features/admin/pages/AdminPage";

export const router = createBrowserRouter([
  { path: "/privacy",  element: <LegalPage slug="privacy" />, errorElement: <RouteErrorFallback /> },
  { path: "/terms",    element: <LegalPage slug="terms" />, errorElement: <RouteErrorFallback /> },
  { path: "/cookies",  element: <LegalPage slug="cookies" />, errorElement: <RouteErrorFallback /> },
  { path: "/about",    element: <LegalPage slug="about" />, errorElement: <RouteErrorFallback /> },
  { path: "/support",  element: <SupportPage />, errorElement: <RouteErrorFallback /> },
  { path: "/docs",     element: <Navigate to="/docs/overview" replace />, errorElement: <RouteErrorFallback /> },
  { path: "/docs/:slug", element: <DocsPage />, errorElement: <RouteErrorFallback /> },
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <RouteErrorFallback />,
    children: [
      // Home (Research Mentor) is the post-login landing; Projects live at /projects.
      { index: true,                                   element: <DashboardPage /> },
      { path: "home",                                  element: <Navigate to="/" replace /> },
      { path: "chat",                                  element: <ChatPage /> },
      { path: "c/:conversationId",                     element: <ChatPage /> },
      { path: "projects",                              element: <ProjectsPage /> },
      { path: "projects/:projectId",                   element: <ProjectDetailPage /> },
      {
        path: "projects/:projectId/writing",
        element: <ProjectWritingRedirect />,
      },
      // Library — canonical /library; /files kept as alias
      { path: "library",                               element: <FilesPage /> },
      { path: "files",                                 element: <RedirectPreserveSearch to="/library" /> },
      { path: "papers/:fileId",                        element: <PaperOverviewPage /> },
      { path: "papers/:fileId/chat",                   element: <PaperChatPage /> },
      { path: "papers/:fileId/chat/:conversationId",   element: <PaperChatPage /> },
      // Compare — canonical /research/compare; /analysis/compare kept as alias
      { path: "research/compare",                      element: <MultiPaperAnalysisPage /> },
      { path: "analysis/compare",                      element: <RedirectPreserveSearch to="/research/compare" /> },
      { path: "citations",                             element: <CitationsPage /> },
      { path: "notes",                                 element: <NotesPage /> },
      { path: "memory",                                element: <MemoryPage /> },
      { path: "search",                                element: <SearchPage /> },
      { path: "writing",                               element: <WritingWorkspacePage /> },
      { path: "settings",                              element: <SettingsPage /> },
      { path: "settings/:section",                     element: <SettingsPage /> },
      { path: "admin",                                 element: <AdminPage /> },
      { path: "admin/:section",                        element: <AdminPage /> },
      { path: "*",                                     element: <Navigate to="/" replace /> },
    ],
  },
]);
