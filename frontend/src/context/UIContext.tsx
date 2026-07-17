import { createContext, useContext, useState, type ReactNode } from "react";
import type { SearchMode } from "@/types/api";

type ActiveView = "chat" | "library" | "projects" | "citations" | "memory" | "settings" | "paper";

interface UIContextValue {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  rightPanelOpen: boolean;
  setRightPanelOpen: (v: boolean) => void;
  currentProjectId: number | null;
  setCurrentProjectId: (id: number | null) => void;
  activeView: ActiveView;
  setActiveView: (v: ActiveView) => void;
  defaultModel: string | null;
  setDefaultModel: (m: string) => void;
  defaultSearchMode: SearchMode;
  setDefaultSearchMode: (m: SearchMode) => void;
}

const UIContext = createContext<UIContextValue | null>(null);

export function UIProvider({ children }: { children: ReactNode }) {
  const [sidebarCollapsed,  setSidebarCollapsed]  = useState(false);
  const [rightPanelOpen,    setRightPanelOpen]    = useState(false);
  const [currentProjectId,  setCurrentProjectId]  = useState<number | null>(null);
  const [activeView,        setActiveView]         = useState<ActiveView>("chat");
  const [defaultModel, setDefaultModelState] = useState<string | null>(
    () => localStorage.getItem("defModel"),
  );
  const [defaultSearchMode, setDefaultSearchModeState] = useState<SearchMode>(
    () => (localStorage.getItem("defSearch") as SearchMode) || "auto",
  );

  const setDefaultModel = (m: string) => {
    localStorage.setItem("defModel", m);
    setDefaultModelState(m);
  };
  const setDefaultSearchMode = (m: SearchMode) => {
    localStorage.setItem("defSearch", m);
    setDefaultSearchModeState(m);
  };

  return (
    <UIContext.Provider
      value={{
        sidebarCollapsed,  setSidebarCollapsed,
        rightPanelOpen,    setRightPanelOpen,
        currentProjectId,  setCurrentProjectId,
        activeView,        setActiveView,
        defaultModel,      setDefaultModel,
        defaultSearchMode, setDefaultSearchMode,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  const ctx = useContext(UIContext);
  if (!ctx) throw new Error("useUI must be used within UIProvider");
  return ctx;
}
