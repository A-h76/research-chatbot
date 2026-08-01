import { createContext, useContext, useState, type ReactNode } from "react";
import type { SearchMode } from "@/types/api";

type ActiveView = "chat" | "library" | "projects" | "citations" | "memory" | "settings" | "paper";

export const SIDEBAR_WIDTH_MIN = 240;
export const SIDEBAR_WIDTH_DEFAULT = 280;
export const SIDEBAR_WIDTH_MAX = 380;
const SIDEBAR_WIDTH_KEY = "dhund.sidebarWidth";

function clampSidebarWidth(n: number): number {
  return Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, Math.round(n)));
}

function readStoredSidebarWidth(): number {
  try {
    const raw = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    if (!raw) return SIDEBAR_WIDTH_DEFAULT;
    const n = Number(raw);
    if (!Number.isFinite(n)) return SIDEBAR_WIDTH_DEFAULT;
    return clampSidebarWidth(n);
  } catch {
    return SIDEBAR_WIDTH_DEFAULT;
  }
}

interface UIContextValue {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  sidebarWidth: number;
  setSidebarWidth: (w: number) => void;
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidthState] = useState(readStoredSidebarWidth);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [defaultModel, setDefaultModelState] = useState<string | null>(
    () => localStorage.getItem("defModel"),
  );
  const [defaultSearchMode, setDefaultSearchModeState] = useState<SearchMode>(
    () => (localStorage.getItem("defSearch") as SearchMode) || "auto",
  );

  const setSidebarWidth = (w: number) => {
    const next = clampSidebarWidth(w);
    setSidebarWidthState(next);
    try {
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(next));
    } catch {
      /* ignore */
    }
  };

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
        sidebarCollapsed,
        setSidebarCollapsed,
        sidebarWidth,
        setSidebarWidth,
        rightPanelOpen,
        setRightPanelOpen,
        currentProjectId,
        setCurrentProjectId,
        activeView,
        setActiveView,
        defaultModel,
        setDefaultModel,
        defaultSearchMode,
        setDefaultSearchMode,
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
