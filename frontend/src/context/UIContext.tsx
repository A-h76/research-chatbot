import { createContext, useContext, useState, type ReactNode } from "react";
import type { SearchMode } from "@/types/api";

type ActiveView = "chat" | "library" | "projects" | "citations" | "memory" | "settings" | "paper";

/** Icon rail when collapsed (VS Code / Cursor style). */
export const SIDEBAR_COLLAPSED_WIDTH = 64;
/** Expanded resize floor — 10.5rem. */
export const SIDEBAR_WIDTH_MIN = 168;
export const SIDEBAR_WIDTH_DEFAULT = 168;
export const SIDEBAR_WIDTH_MAX = 280;
/** Dragging below this snaps to the collapsed rail. */
export const SIDEBAR_SNAP_COLLAPSE = 112;

const SIDEBAR_WIDTH_KEY = "dhund.sidebarWidth.v2";
const SIDEBAR_COLLAPSED_KEY = "dhund.sidebarCollapsed";
const CURRENT_PROJECT_KEY = "dhund.currentProjectId";

function clampExpandedWidth(n: number): number {
  return Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, Math.round(n)));
}

function readStoredSidebarWidth(): number {
  try {
    const raw = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    if (!raw) return SIDEBAR_WIDTH_DEFAULT;
    const n = Number(raw);
    if (!Number.isFinite(n)) return SIDEBAR_WIDTH_DEFAULT;
    return clampExpandedWidth(n);
  } catch {
    return SIDEBAR_WIDTH_DEFAULT;
  }
}

function readStoredCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function readStoredProjectId(): number | null {
  try {
    const raw = localStorage.getItem(CURRENT_PROJECT_KEY);
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  } catch {
    return null;
  }
}

interface UIContextValue {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  /** Last expanded width (168–280). Not the collapsed rail width. */
  sidebarWidth: number;
  setSidebarWidth: (w: number) => void;
  /** Layout width currently shown in the shell. */
  sidebarRailWidth: number;
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
  const [sidebarCollapsed, setSidebarCollapsedState] = useState(readStoredCollapsed);
  const [sidebarWidth, setSidebarWidthState] = useState(readStoredSidebarWidth);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [currentProjectId, setCurrentProjectIdState] = useState<number | null>(readStoredProjectId);

  const setCurrentProjectId = (id: number | null) => {
    setCurrentProjectIdState(id);
    try {
      if (id == null) localStorage.removeItem(CURRENT_PROJECT_KEY);
      else localStorage.setItem(CURRENT_PROJECT_KEY, String(id));
    } catch {
      /* ignore */
    }
  };
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [defaultModel, setDefaultModelState] = useState<string | null>(
    () => localStorage.getItem("defModel"),
  );
  const [defaultSearchMode, setDefaultSearchModeState] = useState<SearchMode>(
    () => (localStorage.getItem("defSearch") as SearchMode) || "auto",
  );

  const setSidebarCollapsed = (v: boolean) => {
    setSidebarCollapsedState(v);
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, v ? "1" : "0");
    } catch {
      /* ignore */
    }
  };

  const setSidebarWidth = (w: number) => {
    const next = clampExpandedWidth(w);
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

  const sidebarRailWidth = sidebarCollapsed
    ? SIDEBAR_COLLAPSED_WIDTH
    : sidebarWidth;

  return (
    <UIContext.Provider
      value={{
        sidebarCollapsed,
        setSidebarCollapsed,
        sidebarWidth,
        setSidebarWidth,
        sidebarRailWidth,
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
