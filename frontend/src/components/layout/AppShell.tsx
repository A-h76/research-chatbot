import { useEffect, useState, type ReactNode } from "react";
import { Sidebar } from "@/features/sidebar/components/Sidebar";
import { MobileDrawer } from "./MobileDrawer";
import { TopBar } from "./TopBar";
import { RightPanel } from "@/features/right-panel/components/RightPanel";
import { useUI } from "@/context/UIContext";
import type { Me } from "@/types/api";

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { sidebarCollapsed, setSidebarCollapsed } = useUI();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setSidebarCollapsed(!sidebarCollapsed);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarCollapsed, setSidebarCollapsed]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar me={me} />
      <MobileDrawer me={me} open={mobileOpen} onOpenChange={setMobileOpen} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onOpenMobileDrawer={() => setMobileOpen(true)} />
        <div className="min-h-0 flex-1">{children}</div>
      </div>
      <RightPanel />
    </div>
  );
}
