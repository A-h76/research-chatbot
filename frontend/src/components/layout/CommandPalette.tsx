/**
 * Research Command Center — ⌘K.
 * Group by intention, not object type:
 * Recommended → Continue → Research → Create → Import → Integrations → Navigate → Recent
 * Prefix modes still work: / skills · @ mention · # entities · > commands
 */
import { useEffect, useMemo, useState, type ComponentType } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  BookOpen,
  Cloud,
  FileDown,
  FileText,
  FolderKanban,
  FolderOpen,
  GitCompare,
  Home,
  Library,
  Link2,
  MessageSquare,
  Network,
  Plus,
  Quote,
  Search,
  Settings,
  StickyNote,
  Upload,
  Wand2,
  Brain,
  LayoutList,
  FlaskConical,
  Tags,
  Table2,
  ClipboardList,
  PenLine,
  ArrowRight,
  Layers,
  Shield,
  Sparkles,
} from "lucide-react";
import { useAllFiles } from "@/features/files/useFiles";
import { useProjects } from "@/features/projects/useProjects";
import {
  projectExportUrl,
  projectHubUrl,
  projectReviewUrl,
  projectWritingUrl,
} from "@/features/projects/projectWorkspaceNav";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useMe } from "@/features/profile/useMe";
import { assistantApi } from "@/features/assistant/api";
import { useUI } from "@/context/UIContext";
import type { ConversationSummary, Project, UserFile } from "@/types/api";

type Surface =
  | "home"
  | "library"
  | "paper"
  | "project"
  | "writing"
  | "ri"
  | "search"
  | "other";

type Scope = {
  surface: Surface;
  label: string;
  paperId: number | null;
  projectId: number | null;
};

type Ranked<T> = { item: T; score: number };

type Cmd = {
  id: string;
  label: string;
  hint?: string;
  keywords: string;
  icon: ComponentType<{ className?: string }>;
  show: boolean;
  /** Boost when idle on matching surfaces */
  surfaces?: Surface[];
  run: () => void;
};

type PrefixMode = "none" | "command" | "mention" | "entity" | "skill";

function scoreMatch(haystack: string, q: string): number {
  if (!q) return 0;
  const h = haystack.toLowerCase();
  if (h === q) return 200;
  if (h.startsWith(q)) return 140;
  const idx = h.indexOf(q);
  if (idx === 0) return 140;
  if (idx > 0) return 80 - Math.min(idx, 40);
  let qi = 0;
  for (let i = 0; i < h.length && qi < q.length; i++) {
    if (h[i] === q[qi]) qi++;
  }
  return qi === q.length ? 30 : -1;
}

function parseRouteIds(pathname: string): {
  paperId: number | null;
  projectId: number | null;
} {
  const paper = pathname.match(/^\/papers\/(\d+)/);
  if (paper) return { paperId: Number(paper[1]), projectId: null };
  const project = pathname.match(/^\/projects\/(\d+)/);
  if (project) return { paperId: null, projectId: Number(project[1]) };
  return { paperId: null, projectId: null };
}

function resolveScope(pathname: string, currentProjectId: number | null): Scope {
  const { paperId, projectId: routeProjectId } = parseRouteIds(pathname);
  if (paperId != null) {
    return { surface: "paper", label: "Paper", paperId, projectId: currentProjectId };
  }
  if (pathname.includes("/writing")) {
    return {
      surface: "writing",
      label: "Writing",
      paperId: null,
      projectId: routeProjectId ?? currentProjectId,
    };
  }
  if (pathname.startsWith("/research") || pathname.startsWith("/analysis")) {
    return {
      surface: "ri",
      label: "Research Intelligence",
      paperId: null,
      projectId: currentProjectId,
    };
  }
  if (routeProjectId != null) {
    return {
      surface: "project",
      label: "Project",
      paperId: null,
      projectId: routeProjectId,
    };
  }
  if (pathname.startsWith("/library") || pathname.startsWith("/files")) {
    return {
      surface: "library",
      label: currentProjectId ? "Library · project" : "Library",
      paperId: null,
      projectId: currentProjectId,
    };
  }
  if (pathname.startsWith("/search")) {
    return {
      surface: "search",
      label: "Search",
      paperId: null,
      projectId: currentProjectId,
    };
  }
  if (pathname === "/" || pathname.startsWith("/home")) {
    return {
      surface: "home",
      label: "Home",
      paperId: null,
      projectId: currentProjectId,
    };
  }
  return {
    surface: "other",
    label: currentProjectId ? "Project" : "Workspace",
    paperId: null,
    projectId: currentProjectId,
  };
}

function chatPath(c: ConversationSummary): string {
  if (c.file_id) return `/papers/${c.file_id}/chat/${c.id}`;
  return `/c/${c.id}`;
}

function paperTitle(f: UserFile): string {
  return (f.title || f.name || "Untitled").trim();
}

function shortTitle(s: string, max = 42): string {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function parsePrefix(raw: string): { mode: PrefixMode; q: string } {
  const t = raw.trimStart();
  if (t.startsWith(">")) return { mode: "command", q: t.slice(1).trim().toLowerCase() };
  if (t.startsWith("@")) return { mode: "mention", q: t.slice(1).trim().toLowerCase() };
  if (t.startsWith("#")) return { mode: "entity", q: t.slice(1).trim().toLowerCase() };
  if (t.startsWith("/")) return { mode: "skill", q: t.slice(1).trim().toLowerCase() };
  return { mode: "none", q: t.trim().toLowerCase() };
}

function filterCmds(list: Cmd[], q: string, surface?: Surface): Cmd[] {
  const visible = list.filter((c) => c.show);
  if (!q) {
    // Surface-aware ordering when idle
    return [...visible].sort((a, b) => {
      const aBoost = surface && a.surfaces?.includes(surface) ? 1 : 0;
      const bBoost = surface && b.surfaces?.includes(surface) ? 1 : 0;
      return bBoost - aBoost;
    });
  }
  return visible
    .map((c) => ({
      cmd: c,
      score: scoreMatch(`${c.label} ${c.keywords} ${c.hint ?? ""}`, q),
    }))
    .filter((x) => x.score >= 0)
    .sort((a, b) => b.score - a.score)
    .map((x) => x.cmd);
}

function isNeedsPdf(f: UserFile): boolean {
  if (f.kind !== "document") return false;
  if (f.has_pdf === false) return true;
  if (f.research_readiness === "metadata_only") return true;
  if (!f.research_readiness && (f.size === 0 || !f.size)) return true;
  return false;
}

function pickContinuePaper(files: UserFile[], projectId: number | null): UserFile | null {
  const docs = files.filter((f) => f.kind === "document" && !isNeedsPdf(f));
  const scoped =
    projectId != null ? docs.filter((f) => f.project_id === projectId) : docs;
  const pool = scoped.length ? scoped : docs;
  return (
    pool.find((f) => f.reading_status === "reading") ??
    pool.find((f) => f.reading_status === "unread" || !f.reading_status) ??
    pool[0] ??
    null
  );
}

/**
 * Research Command Center — ⌘K / sidebar Search.
 * Intention-first: where do I want to go, or what do I want to do?
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const { currentProjectId, setCurrentProjectId } = useUI();

  const { data: files = [] } = useAllFiles();
  const { data: projects = [] } = useProjects();
  const { data: conversations = [] } = useConversations();
  const { data: me } = useMe();
  const { data: researchState } = useQuery({
    queryKey: ["assistant", "research-state", "cmdk", currentProjectId ?? null],
    queryFn: () => assistantApi.researchState(currentProjectId),
    staleTime: 60_000,
    enabled: open,
  });

  const scope = useMemo(
    () => resolveScope(location.pathname, currentProjectId),
    [location.pathname, currentProjectId],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("soro:command-palette", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("soro:command-palette", onOpen);
    };
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const { mode, q } = parsePrefix(query);
  const paperId = scope.paperId;

  function go(path: string) {
    setOpen(false);
    navigate(path);
  }

  function writingPath(
    opts?: { focus?: "evidence" | "review"; tab?: "export"; action?: "lit-review" },
  ): string {
    if (currentProjectId != null) {
      return projectWritingUrl(currentProjectId, opts);
    }
    const params = new URLSearchParams();
    if (opts?.focus) params.set("focus", opts.focus);
    if (opts?.tab) params.set("tab", opts.tab);
    if (opts?.action) params.set("action", opts.action);
    const qs = params.toString();
    return qs ? `/writing?${qs}` : "/writing";
  }

  function run(fn: () => void) {
    setOpen(false);
    fn();
  }

  const activeProject = useMemo(() => {
    const id = scope.projectId ?? currentProjectId;
    if (id == null) return null;
    return projects.find((p) => p.id === id) ?? null;
  }, [projects, scope.projectId, currentProjectId]);

  const continuePaper = useMemo(
    () => pickContinuePaper(files, scope.projectId),
    [files, scope.projectId],
  );

  const rankedPapers = useMemo(() => {
    const ranked: Ranked<UserFile>[] = [];
    for (const f of files) {
      if (f.kind !== "document") continue;
      const blob = [paperTitle(f), f.authors, f.year, f.venue, f.doi, ...(f.tags ?? [])]
        .filter(Boolean)
        .join(" ");
      let score = scoreMatch(blob, q);
      if (!q) {
        const ts = f.created_at ? Date.parse(f.created_at) : 0;
        score = (Number.isFinite(ts) ? ts : 0) / 1000 + f.id;
        if (scope.projectId != null && f.project_id === scope.projectId) score += 1e9;
        if (scope.paperId != null && f.id === scope.paperId) score += 2e9;
      } else if (score < 0) {
        continue;
      } else if (scope.projectId != null && f.project_id === scope.projectId) {
        score += 15;
      }
      ranked.push({ item: f, score });
    }
    ranked.sort((a, b) => b.score - a.score);
    return ranked.slice(0, q ? 8 : 5).map((r) => r.item);
  }, [files, q, scope.paperId, scope.projectId]);

  const rankedProjects = useMemo(() => {
    const ranked: Ranked<Project>[] = [];
    for (const p of projects) {
      const blob = `${p.name} ${p.description} ${p.emoji}`;
      let score = scoreMatch(blob, q);
      if (!q) {
        score = 10;
        if (scope.projectId === p.id) score += 30;
      } else if (score < 0) {
        continue;
      }
      ranked.push({ item: p, score });
    }
    ranked.sort((a, b) => b.score - a.score);
    return ranked.slice(0, q ? 6 : 4).map((r) => r.item);
  }, [projects, q, scope.projectId]);

  const rankedChats = useMemo(() => {
    const ranked: Ranked<ConversationSummary>[] = [];
    for (const c of conversations) {
      const blob = `${c.title} chat conversation note`;
      let score = scoreMatch(blob, q);
      if (!q) {
        score = 10;
        if (scope.projectId != null && c.project_id === scope.projectId) score += 20;
        if (scope.paperId != null && c.file_id === scope.paperId) score += 25;
      } else if (score < 0) {
        continue;
      }
      ranked.push({ item: c, score });
    }
    ranked.sort((a, b) => b.score - a.score);
    return ranked.slice(0, q ? 6 : 4).map((r) => r.item);
  }, [conversations, q, scope.paperId, scope.projectId]);

  const recommended: Cmd[] = useMemo(() => {
    const na = researchState?.workflow?.nextAction;
    if (!na?.label || !na.href) return [];
    return [
      {
        id: "rs-next",
        label: na.label,
        hint: researchState?.workflow?.label || "Recommended",
        keywords: `recommended next ${na.label} ${researchState?.workflow?.stage ?? ""}`,
        icon: Sparkles,
        show: true,
        run: () => go(na.href.startsWith("/") ? na.href : `/${na.href}`),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [researchState?.workflow?.nextAction, researchState?.workflow?.label, researchState?.workflow?.stage]);

  const continueCmds: Cmd[] = useMemo(() => {
    const cmds: Cmd[] = [];
    if (activeProject) {
      const next = researchState?.workflow?.nextAction?.label;
      cmds.push({
        id: "continue-project",
        label: next
          ? `Continue ${activeProject.name}`
          : `Continue ${activeProject.name}`,
        hint: next || "Project",
        keywords: `continue project research ${activeProject.name}`,
        icon: ArrowRight,
        show: true,
        surfaces: ["home", "project", "other"],
        run: () => {
          const href =
            researchState?.workflow?.nextAction?.href ||
            projectHubUrl(activeProject.id);
          setCurrentProjectId(activeProject.id);
          go(href.startsWith("/") ? href : `/${href}`);
        },
      });
    }
    if (continuePaper) {
      const reading = continuePaper.reading_status === "reading";
      cmds.push({
        id: "continue-paper",
        label: reading
          ? `Continue reading “${shortTitle(paperTitle(continuePaper))}”`
          : `Read “${shortTitle(paperTitle(continuePaper))}”`,
        hint: reading ? "Reading" : "Recommended",
        keywords: `continue reading paper ${paperTitle(continuePaper)}`,
        icon: BookOpen,
        show: true,
        surfaces: ["library", "home", "paper"],
        run: () => go(`/papers/${continuePaper.id}`),
      });
    }
    if (activeProject || currentProjectId != null) {
      const pid = activeProject?.id ?? currentProjectId!;
      cmds.push({
        id: "continue-writing",
        label: "Continue writing",
        hint: "Manuscript",
        keywords: "continue writing manuscript chapter draft",
        icon: PenLine,
        show: true,
        surfaces: ["writing", "project", "home"],
        run: () => go(projectWritingUrl(pid)),
      });
    }
    return cmds;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeProject,
    continuePaper,
    currentProjectId,
    researchState?.workflow?.nextAction,
  ]);

  const researchCmds: Cmd[] = useMemo(
    () => [
      {
        id: "mentor",
        label: "Ask Research Mentor",
        hint: "Home",
        keywords: "mentor ask help topic orient",
        icon: MessageSquare,
        show: true,
        surfaces: ["home", "project"],
        run: () => go("/"),
      },
      {
        id: "ask",
        label: "Ask Dhund",
        hint: "Chat",
        keywords: "ask chat agent conversation",
        icon: MessageSquare,
        show: true,
        surfaces: ["paper", "writing", "ri"],
        run: () => go(paperId ? `/papers/${paperId}/chat` : "/chat"),
      },
      {
        id: "ri",
        label: "Research Intelligence",
        hint: "Corpus",
        keywords: "research intelligence compare gaps themes matrix",
        icon: GitCompare,
        show: true,
        surfaces: ["ri", "project", "library"],
        run: () => go("/research/compare"),
      },
      {
        id: "search-lit",
        label: "Search literature",
        hint: "Discover",
        keywords: "search literature discover pubmed openalex",
        icon: Search,
        show: true,
        surfaces: ["search", "library", "home"],
        run: () => go("/search"),
      },
      {
        id: "evidence",
        label: "Review evidence",
        hint: "Evidence",
        keywords: "evidence inspector review passages",
        icon: FlaskConical,
        show: true,
        surfaces: ["writing", "ri", "paper"],
        run: () =>
          go(
            paperId
              ? `/papers/${paperId}?tab=evidence`
              : writingPath({ focus: "evidence" }),
          ),
      },
      {
        id: "matrix",
        label: "Evidence matrix",
        hint: "RI",
        keywords: "matrix methods findings evidence",
        icon: Table2,
        show: true,
        surfaces: ["ri"],
        run: () => go("/research/compare?tab=matrix"),
      },
      {
        id: "themes",
        label: "Themes",
        hint: "RI",
        keywords: "themes clusters narrative",
        icon: Tags,
        show: true,
        surfaces: ["ri"],
        run: () => go("/research/compare?tab=themes"),
      },
      {
        id: "gaps",
        label: "Research gaps",
        hint: "RI",
        keywords: "gaps research missing",
        icon: LayoutList,
        show: true,
        surfaces: ["ri"],
        run: () => go("/research/compare?tab=gaps"),
      },
      {
        id: "graph",
        label: "Knowledge graph",
        hint: paperId ? "Paper" : "RI",
        keywords: "graph knowledge network",
        icon: Network,
        show: true,
        surfaces: ["ri", "paper"],
        run: () =>
          go(paperId ? `/papers/${paperId}?tab=graph` : "/research/compare?tab=graph"),
      },
      {
        id: "extract",
        label: "Extract evidence",
        hint: "RI",
        keywords: "extract pico structured evidence",
        icon: ClipboardList,
        show: true,
        surfaces: ["ri", "library", "paper"],
        run: () => go("/research/compare?tab=extract"),
      },
      {
        id: "reviewer",
        label: "Review before publish",
        hint: "Review",
        keywords: "review verify publish writing",
        icon: Shield,
        show: true,
        surfaces: ["writing"],
        run: () =>
          go(
            currentProjectId != null
              ? projectReviewUrl(currentProjectId)
              : writingPath({ focus: "review" }),
          ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [paperId, currentProjectId],
  );

  const createCmds: Cmd[] = useMemo(
    () => [
      {
        id: "new-research",
        label: "New research",
        hint: "Project",
        keywords: "new create project research workspace",
        icon: Plus,
        show: true,
        surfaces: ["home", "project"],
        run: () => go("/projects?new=1"),
      },
      {
        id: "new-manuscript",
        label: "New manuscript",
        hint: "Writing",
        keywords: "write literature review manuscript draft",
        icon: PenLine,
        show: true,
        surfaces: ["writing", "project"],
        run: () => go(writingPath({ action: "lit-review" })),
      },
      {
        id: "new-note",
        label: "New note",
        hint: "Notes",
        keywords: "note sticky memo",
        icon: StickyNote,
        show: true,
        run: () => go("/notes"),
      },
      {
        id: "new-collection",
        label: "New collection",
        hint: "Library",
        keywords: "collection folder organize",
        icon: Layers,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?collections=1"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentProjectId],
  );

  const importCmds: Cmd[] = useMemo(
    () => [
      {
        id: "upload",
        label: "Upload PDF",
        hint: "Import",
        keywords: "upload pdf paper document",
        icon: Upload,
        show: true,
        surfaces: ["library", "home"],
        run: () => go("/library?upload=1"),
      },
      {
        id: "import-doi",
        label: "Import DOI",
        hint: "Import",
        keywords: "import doi crossref discover",
        icon: Link2,
        show: true,
        surfaces: ["library", "search"],
        run: () => go("/search?mode=discover&q=10."),
      },
      {
        id: "import-pmid",
        label: "Import PMID",
        hint: "Import",
        keywords: "import pmid pubmed",
        icon: Link2,
        show: true,
        surfaces: ["library", "search"],
        run: () => go("/search?mode=discover&provider=pubmed"),
      },
      {
        id: "import-bibtex",
        label: "Import BibTeX / RIS",
        hint: "Import",
        keywords: "import bibtex ris reference",
        icon: FileDown,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?provider=bibtex"),
      },
      {
        id: "merge-dups",
        label: "Merge duplicates",
        hint: "Maintenance",
        keywords: "merge duplicates library health",
        icon: Layers,
        show: true,
        surfaces: ["library"],
        run: () => go("/library"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const integrationCmds: Cmd[] = useMemo(
    () => [
      {
        id: "pubmed",
        label: "PubMed",
        hint: "Literature",
        keywords: "pubmed medline integrate search",
        icon: Search,
        show: true,
        run: () => go("/search?mode=discover&provider=pubmed"),
      },
      {
        id: "scholar",
        label: "Google Scholar",
        hint: "Literature",
        keywords: "google scholar search",
        icon: Search,
        show: true,
        run: () => go("/search?mode=discover"),
      },
      {
        id: "crossref",
        label: "Crossref",
        hint: "Literature",
        keywords: "crossref doi",
        icon: Link2,
        show: true,
        run: () => go("/search?mode=discover&q=10."),
      },
      {
        id: "semantic",
        label: "Semantic Scholar",
        hint: "Literature",
        keywords: "semantic scholar openalex",
        icon: Search,
        show: true,
        run: () => go("/search?mode=discover"),
      },
      {
        id: "arxiv",
        label: "arXiv",
        hint: "Literature",
        keywords: "arxiv preprint",
        icon: FileText,
        show: true,
        run: () => go("/search?mode=discover&provider=arxiv"),
      },
      {
        id: "zotero",
        label: "Zotero",
        hint: "Reference manager",
        keywords: "zotero import sync",
        icon: FolderOpen,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?provider=zotero#import"),
      },
      {
        id: "mendeley",
        label: "Mendeley",
        hint: "Reference manager",
        keywords: "mendeley import sync",
        icon: FolderOpen,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?provider=mendeley#import"),
      },
      {
        id: "endnote",
        label: "EndNote / RIS",
        hint: "Reference manager",
        keywords: "endnote ris import",
        icon: FolderOpen,
        show: true,
        run: () => go("/library?provider=bibtex"),
      },
      {
        id: "gdrive",
        label: "Google Drive",
        hint: "Cloud",
        keywords: "google drive cloud import",
        icon: Cloud,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?provider=google_drive#import"),
      },
      {
        id: "dropbox",
        label: "Dropbox",
        hint: "Cloud",
        keywords: "dropbox cloud import",
        icon: Cloud,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?provider=dropbox#import"),
      },
      {
        id: "onedrive",
        label: "OneDrive",
        hint: "Cloud",
        keywords: "onedrive cloud import",
        icon: Cloud,
        show: true,
        surfaces: ["library"],
        run: () => go("/library?provider=onedrive#import"),
      },
      {
        id: "integrations-settings",
        label: "Manage integrations",
        hint: "Settings",
        keywords: "integrations settings connect oauth",
        icon: Settings,
        show: true,
        run: () => go("/settings/integrations"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const navigateCmds: Cmd[] = useMemo(
    () => [
      {
        id: "nav-home",
        label: "Home",
        hint: "Navigate",
        keywords: "home launchpad dashboard mentor",
        icon: Home,
        show: true,
        run: () => go("/"),
      },
      {
        id: "nav-projects",
        label: "Projects",
        hint: "Navigate",
        keywords: "projects research list",
        icon: FolderKanban,
        show: true,
        run: () => go("/projects"),
      },
      {
        id: "nav-library",
        label: "Library",
        hint: "Navigate",
        keywords: "library papers files",
        icon: Library,
        show: true,
        run: () => go("/library"),
      },
      {
        id: "nav-writing",
        label: "Writing",
        hint: "Navigate",
        keywords: "writing desk draft manuscript",
        icon: Wand2,
        show: true,
        run: () => go(writingPath()),
      },
      {
        id: "nav-evidence",
        label: "Evidence",
        hint: "Navigate",
        keywords: "evidence inspector",
        icon: FlaskConical,
        show: true,
        run: () => go(writingPath({ focus: "evidence" })),
      },
      {
        id: "nav-ri",
        label: "Research Intelligence",
        hint: "Navigate",
        keywords: "research intelligence compare",
        icon: GitCompare,
        show: true,
        run: () => go("/research/compare"),
      },
      {
        id: "nav-review",
        label: "Review",
        hint: "Navigate",
        keywords: "review publish",
        icon: Shield,
        show: true,
        run: () =>
          go(
            currentProjectId != null
              ? projectReviewUrl(currentProjectId)
              : writingPath({ focus: "review" }),
          ),
      },
      {
        id: "nav-notes",
        label: "Notes",
        hint: "Navigate",
        keywords: "notes",
        icon: StickyNote,
        show: true,
        run: () => go("/notes"),
      },
      {
        id: "nav-citations",
        label: "Citations",
        hint: "Navigate",
        keywords: "citations export apa bibtex",
        icon: Quote,
        show: true,
        run: () => go("/citations"),
      },
      {
        id: "nav-memory",
        label: "Memory",
        hint: "Navigate",
        keywords: "memory preferences claims",
        icon: Brain,
        show: true,
        run: () => go("/memory"),
      },
      {
        id: "nav-settings",
        label: "Settings",
        hint: "Navigate",
        keywords: "settings account preferences",
        icon: Settings,
        show: true,
        run: () => go("/settings"),
      },
      {
        id: "nav-admin",
        label: "Admin",
        hint: "Navigate",
        keywords: "admin ops",
        icon: Shield,
        show: Boolean(me?.is_admin),
        run: () => go("/admin"),
      },
      {
        id: "nav-export",
        label: "Publish / export",
        hint: "Navigate",
        keywords: "export publish markdown",
        icon: FileDown,
        show: true,
        run: () =>
          go(
            currentProjectId != null
              ? projectExportUrl(currentProjectId)
              : writingPath({ tab: "export" }),
          ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [me?.is_admin, currentProjectId],
  );

  const paperKnowledge: Cmd[] = useMemo(
    () => [
      {
        id: "paper-overview",
        label: "Research profile",
        hint: "Paper",
        keywords: "research profile overview summary",
        icon: FileText,
        show: paperId != null,
        surfaces: ["paper"],
        run: () => go(`/papers/${paperId}`),
      },
      {
        id: "paper-entities",
        label: "Entities",
        hint: "Paper",
        keywords: "entities concepts pico",
        icon: Tags,
        show: paperId != null,
        surfaces: ["paper"],
        run: () => go(`/papers/${paperId}?tab=entities`),
      },
      {
        id: "paper-structure",
        label: "Structure",
        hint: "Paper",
        keywords: "structure sections outline",
        icon: LayoutList,
        show: paperId != null,
        surfaces: ["paper"],
        run: () => go(`/papers/${paperId}?tab=structure`),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [paperId],
  );

  const allActionCmds = useMemo(
    () => [
      ...recommended,
      ...continueCmds,
      ...researchCmds,
      ...createCmds,
      ...importCmds,
      ...integrationCmds,
      ...navigateCmds,
      ...paperKnowledge,
    ],
    [
      recommended,
      continueCmds,
      researchCmds,
      createCmds,
      importCmds,
      integrationCmds,
      navigateCmds,
      paperKnowledge,
    ],
  );

  const idle = mode === "none" && !q;
  const searching = mode === "none" && Boolean(q);

  const shownRecommended = filterCmds(recommended, idle ? "" : q, scope.surface);
  const shownContinue = filterCmds(continueCmds, idle ? "" : q, scope.surface);
  const shownResearch = filterCmds(researchCmds, idle ? "" : q, scope.surface).slice(
    0,
    idle ? 6 : 8,
  );
  const shownCreate = filterCmds(createCmds, idle ? "" : q, scope.surface);
  const shownImport = filterCmds(importCmds, idle ? "" : q, scope.surface);
  const shownIntegrations = filterCmds(
    integrationCmds,
    idle ? "" : q,
    scope.surface,
  ).slice(0, idle ? 8 : 10);
  const shownNavigate = filterCmds(navigateCmds, idle ? "" : q, scope.surface);
  const shownPaper = filterCmds(paperKnowledge, idle ? "" : q, scope.surface);
  const shownSkills = filterCmds(
    [...researchCmds, ...createCmds, ...importCmds],
    q,
    scope.surface,
  );
  const shownCommands = filterCmds(allActionCmds, q, scope.surface);

  const showEmpty =
    !idle &&
    shownRecommended.length === 0 &&
    shownContinue.length === 0 &&
    shownResearch.length === 0 &&
    shownCreate.length === 0 &&
    shownImport.length === 0 &&
    shownIntegrations.length === 0 &&
    shownNavigate.length === 0 &&
    shownPaper.length === 0 &&
    shownSkills.length === 0 &&
    shownCommands.length === 0 &&
    rankedPapers.length === 0 &&
    rankedProjects.length === 0 &&
    rankedChats.length === 0;

  function renderCmd(c: Cmd) {
    const Icon = c.icon;
    return (
      <CommandItem key={c.id} value={c.id} onSelect={() => run(c.run)} className="gap-2">
        <Icon className="size-4 shrink-0 text-muted-foreground" />
        <span className="flex-1 truncate">{c.label}</span>
        {c.hint && (
          <span className="shrink-0 text-[11px] text-muted-foreground">{c.hint}</span>
        )}
      </CommandItem>
    );
  }

  function group(heading: string, cmds: Cmd[]) {
    if (cmds.length === 0) return null;
    return <CommandGroup heading={heading}>{cmds.map(renderCmd)}</CommandGroup>;
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Search Dhund"
      description="Where do you want to go, or what do you want to do?"
    >
      <Command shouldFilter={false} className="rounded-xl">
        <CommandInput
          value={query}
          onValueChange={setQuery}
          placeholder="Search papers, projects, evidence, notes…"
        />
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-3 py-1.5 text-[11px] text-muted-foreground">
          <span className="rounded-md border border-border bg-muted/40 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-text-tertiary">
            {scope.label}
          </span>
          <span>
            <kbd className="opacity-70">/</kbd> skills ·{" "}
            <kbd className="opacity-70">@</kbd> mention ·{" "}
            <kbd className="opacity-70">#</kbd> entities ·{" "}
            <kbd className="opacity-70">&gt;</kbd> commands
          </span>
        </div>
        <CommandList className="max-h-[min(460px,58vh)]">
          {showEmpty && <CommandEmpty>No matches.</CommandEmpty>}

          {mode === "skill" && group("Skills", shownSkills)}
          {mode === "command" && group("Commands", shownCommands)}

          {mode === "entity" && (
            <CommandGroup heading="Entities & knowledge">
              {shownPaper.length > 0 ? (
                shownPaper.map(renderCmd)
              ) : (
                <CommandItem value="entity-hint" disabled>
                  <Tags className="size-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {q
                      ? `No entity match for “${q}” — open a paper for entity maps`
                      : "Open a paper, then #jump to entities · graph · structure"}
                  </span>
                </CommandItem>
              )}
            </CommandGroup>
          )}

          {mode === "mention" && (
            <>
              {rankedProjects.length > 0 && (
                <CommandGroup heading="Projects">
                  {rankedProjects.map((p) => (
                    <CommandItem
                      key={`project-${p.id}`}
                      value={`project-${p.id}`}
                      onSelect={() =>
                        run(() => {
                          setCurrentProjectId(p.id);
                          navigate(`/projects/${p.id}`);
                        })
                      }
                      className="gap-2"
                    >
                      <span className="size-4 text-center text-sm leading-4">
                        {p.emoji || "📁"}
                      </span>
                      <span className="min-w-0 flex-1 truncate">{p.name}</span>
                      <span className="text-[11px] text-muted-foreground">Project</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
              {rankedPapers.length > 0 && (
                <CommandGroup heading="Papers">
                  {rankedPapers.map((f) => (
                    <CommandItem
                      key={`paper-${f.id}`}
                      value={`paper-${f.id}`}
                      onSelect={() => go(`/papers/${f.id}`)}
                      className="gap-2"
                    >
                      <BookOpen className="size-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate">{paperTitle(f)}</span>
                      <span className="text-[11px] text-muted-foreground">Paper</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
            </>
          )}

          {idle && (
            <>
              {group("Recommended", shownRecommended)}
              {shownRecommended.length > 0 && shownContinue.length > 0 ? (
                <CommandSeparator />
              ) : null}
              {group("Continue", shownContinue)}
              {(shownRecommended.length > 0 || shownContinue.length > 0) && (
                <CommandSeparator />
              )}
              {group("Research", shownResearch)}
              <CommandSeparator />
              {group("Create", shownCreate)}
              <CommandSeparator />
              {group("Import", shownImport)}
              <CommandSeparator />
              {group("Integrations", shownIntegrations)}
              <CommandSeparator />
              {group("Navigate", shownNavigate)}
              {(rankedPapers.length > 0 ||
                rankedProjects.length > 0 ||
                rankedChats.length > 0) && (
                <>
                  <CommandSeparator />
                  <CommandGroup heading="Recent">
                    {rankedProjects.slice(0, 2).map((p) => (
                      <CommandItem
                        key={`recent-p-${p.id}`}
                        value={`recent-p-${p.id}`}
                        onSelect={() =>
                          run(() => {
                            setCurrentProjectId(p.id);
                            navigate(`/projects/${p.id}`);
                          })
                        }
                        className="gap-2"
                      >
                        <span className="size-4 text-center text-sm leading-4">
                          {p.emoji || "📁"}
                        </span>
                        <span className="min-w-0 flex-1 truncate">{p.name}</span>
                        <span className="text-[11px] text-muted-foreground">Project</span>
                      </CommandItem>
                    ))}
                    {rankedPapers.slice(0, 3).map((f) => (
                      <CommandItem
                        key={`recent-f-${f.id}`}
                        value={`recent-f-${f.id}`}
                        onSelect={() => go(`/papers/${f.id}`)}
                        className="gap-2"
                      >
                        <BookOpen className="size-4 shrink-0 text-muted-foreground" />
                        <span className="min-w-0 flex-1 truncate">{paperTitle(f)}</span>
                        <span className="text-[11px] text-muted-foreground">Paper</span>
                      </CommandItem>
                    ))}
                    {rankedChats.slice(0, 2).map((c) => (
                      <CommandItem
                        key={`recent-c-${c.id}`}
                        value={`recent-c-${c.id}`}
                        onSelect={() => go(chatPath(c))}
                        className="gap-2"
                      >
                        <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                        <span className="min-w-0 flex-1 truncate">
                          {c.title || "Untitled chat"}
                        </span>
                        <span className="text-[11px] text-muted-foreground">Chat</span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </>
              )}
            </>
          )}

          {searching && (
            <>
              {shownRecommended.length > 0 && group("Recommended", shownRecommended)}
              {shownContinue.length > 0 && group("Continue", shownContinue)}
              {shownResearch.length > 0 && group("Research", shownResearch)}
              {shownCreate.length > 0 && group("Create", shownCreate)}
              {shownImport.length > 0 && group("Import", shownImport)}
              {rankedPapers.length > 0 && (
                <CommandGroup heading="Papers">
                  {rankedPapers.map((f) => (
                    <CommandItem
                      key={`hit-paper-${f.id}`}
                      value={`hit-paper-${f.id}`}
                      onSelect={() => go(`/papers/${f.id}`)}
                      className="gap-2"
                    >
                      <BookOpen className="size-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate">{paperTitle(f)}</span>
                      <span className="text-[11px] text-muted-foreground">
                        {[f.year, f.reading_status].filter(Boolean).join(" · ")}
                      </span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
              {rankedProjects.length > 0 && (
                <CommandGroup heading="Projects">
                  {rankedProjects.map((p) => (
                    <CommandItem
                      key={`hit-project-${p.id}`}
                      value={`hit-project-${p.id}`}
                      onSelect={() =>
                        run(() => {
                          setCurrentProjectId(p.id);
                          navigate(`/projects/${p.id}`);
                        })
                      }
                      className="gap-2"
                    >
                      <span className="size-4 text-center text-sm leading-4">
                        {p.emoji || "📁"}
                      </span>
                      <span className="min-w-0 flex-1 truncate">{p.name}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
              {rankedChats.length > 0 && (
                <CommandGroup heading="Chats & notes">
                  {rankedChats.map((c) => (
                    <CommandItem
                      key={`hit-chat-${c.id}`}
                      value={`hit-chat-${c.id}`}
                      onSelect={() => go(chatPath(c))}
                      className="gap-2"
                    >
                      <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate">
                        {c.title || "Untitled chat"}
                      </span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
              {shownIntegrations.length > 0 &&
                group("Integrations", shownIntegrations.slice(0, 5))}
              {shownNavigate.length > 0 && group("Navigate", shownNavigate.slice(0, 6))}
              {q && (
                <CommandGroup heading="Library">
                  <CommandItem
                    value="find-library"
                    onSelect={() =>
                      go(`/library?q=${encodeURIComponent(query.trim())}`)
                    }
                    className="gap-2"
                  >
                    <Library className="size-4 text-muted-foreground" />
                    <span className="truncate">Find in library: “{query.trim()}”</span>
                  </CommandItem>
                </CommandGroup>
              )}
            </>
          )}
        </CommandList>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border px-3 py-2 text-[10px] text-muted-foreground">
          <span>↑↓ Navigate</span>
          <span>Enter Open</span>
          <span>Esc Close</span>
          <span className="ml-auto">⌘K anywhere</span>
        </div>
      </Command>
    </CommandDialog>
  );
}
