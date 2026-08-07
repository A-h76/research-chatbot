import { useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Sidebar } from "@/features/sidebar/components/Sidebar";
import { ProjectJourneySidebar } from "@/features/projects/components/ProjectJourneySidebar";
import { MobileDrawer } from "./MobileDrawer";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";
import { RightPanel } from "@/features/right-panel/components/RightPanel";
import { OnboardingWizard } from "@/features/onboarding/OnboardingWizard";
import { ProjectWorkspaceBar } from "@/features/projects/components/ProjectWorkspaceBar";
import { isProjectWorkspacePath } from "@/features/projects/projectWorkspaceNav";
import { useUI } from "@/context/UIContext";
import { isTypingTarget } from "@/lib/keyboard";
import type { Me } from "@/types/api";

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { sidebarCollapsed, setSidebarCollapsed, currentProjectId } = useUI();
  const location = useLocation();
  const projectWorkspace =
    currentProjectId != null &&
    isProjectWorkspacePath(location.pathname, currentProjectId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setSidebarCollapsed(!sidebarCollapsed);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarCollapsed, setSidebarCollapsed]);

  return (
    <div
      className={`flex h-screen w-screen overflow-hidden bg-background text-foreground${projectWorkspace ? " writing-studio" : ""}`}
    >
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      {projectWorkspace ? (
        <div className="hidden md:flex">
          <ProjectJourneySidebar />
        </div>
      ) : (
        <Sidebar me={me} />
      )}
      <MobileDrawer me={me} open={mobileOpen} onOpenChange={setMobileOpen} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar onOpenMobileDrawer={() => setMobileOpen(true)} me={me} />
        {!projectWorkspace && <ProjectWorkspaceBar />}
        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-0 flex-1 overflow-hidden outline-none"
        >
          {children}
        </main>
      </div>
      <RightPanel />
      <CommandPalette />
      {!me.onboarding_completed && <OnboardingWizard me={me} />}
    </div>
  );
}
