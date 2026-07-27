import { useEffect, useMemo, useState, type ComponentType } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
  FileText,
  FolderKanban,
  GitCompare,
  Home,
  Library,
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
} from "lucide-react";
import { useAllFiles } from "@/features/files/useFiles";
import { useProjects } from "@/features/projects/useProjects";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { cn } from "@/lib/utils";
import type { ConversationSummary, Project, UserFile } from "@/types/api";

type ScopeKind = "paper" | "project" | "library" | "global";

type Scope = {
  kind: ScopeKind;
  label: string;
  paperId: number | null;
  projectId: number | null;
};

type Ranked<T> = { item: T; score: number };

function scoreMatch(haystack: string, q: string): number {
  if (!q) return 0;
  const h = haystack.toLowerCase();
  if (h === q) return 200;
  if (h.startsWith(q)) return 140;
  const idx = h.indexOf(q);
  if (idx === 0) return 140;
  if (idx > 0) return 80 - Math.min(idx, 40);
  // light fuzzy: all query chars in order
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
  if (paper) {
    return { paperId: Number(paper[1]), projectId: null };
  }
  const project = pathname.match(/^\/projects\/(\d+)/);
  if (project) {
    return { paperId: null, projectId: Number(project[1]) };
  }
  return { paperId: null, projectId: null };
}

function resolveScope(pathname: string, currentProjectId: number | null): Scope {
  const { paperId, projectId: routeProjectId } = parseRouteIds(pathname);

  if (paperId != null) {
    return { kind: "paper", label: "Paper", paperId, projectId: currentProjectId };
  }
  if (routeProjectId != null) {
    return { kind: "project", label: "Project", paperId: null, projectId: routeProjectId };
  }
  if (pathname.startsWith("/library") || pathname.startsWith("/files")) {
    return {
      kind: "library",
      label: currentProjectId ? "Library · project" : "Library",
      paperId: null,
      projectId: currentProjectId,
    };
  }
  if (currentProjectId) {
    return {
      kind: "project",
      label: "Project",
      paperId: null,
      projectId: currentProjectId,
    };
  }
  return { kind: "global", label: "Workspace", paperId: null, projectId: null };
}

function chatPath(c: ConversationSummary): string {
  if (c.file_id) return `/papers/${c.file_id}/chat/${c.id}`;
  return `/c/${c.id}`;
}

function paperTitle(f: UserFile): string {
  return (f.title || f.name || "Untitled").trim();
}

/**
 * D8 — ⌘K command palette v1: find (papers / projects / chats) + navigate + core commands.
 * Scope-aware; private library first (no web-wide search).
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

  const q = query.trim().toLowerCase();

  const rankedPapers = useMemo(() => {
    const ranked: Ranked<UserFile>[] = [];
    for (const f of files) {
      if (f.kind !== "document") continue;
      const blob = [
        paperTitle(f),
        f.authors,
        f.year,
        f.venue,
        f.doi,
        ...(f.tags ?? []),
      ]
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
      const blob = `${c.title} chat conversation`;
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

  function go(path: string) {
    setOpen(false);
    navigate(path);
  }

  function run(fn: () => void) {
    setOpen(false);
    fn();
  }

  const paperId = scope.paperId;

  type Cmd = {
    id: string;
    label: string;
    hint?: string;
    keywords: string;
    icon: ComponentType<{ className?: string }>;
    show: boolean;
    run: () => void;
  };

  const visibleCommands = useMemo(() => {
    const commands: Cmd[] = [
      {
        id: "upload",
        label: "Upload paper",
        hint: "Library",
        keywords: "upload paper pdf document add",
        icon: Upload,
        show: true,
        run: () => go("/library?upload=1"),
      },
      {
        id: "search-papers",
        label: "Search papers",
        hint: "Search",
        keywords: "search find papers library rag",
        icon: Search,
        show: true,
        run: () => go("/search"),
      },
      {
        id: "find-library",
        label: q ? `Find in library: “${query.trim()}”` : "Find in library",
        hint: "Library",
        keywords: "find library filter author title",
        icon: Library,
        show: Boolean(q),
        run: () => go(`/library?q=${encodeURIComponent(query.trim())}`),
      },
      {
        id: "compare",
        label: "Compare papers",
        hint: "Tool",
        keywords: "compare gaps multi paper analysis",
        icon: GitCompare,
        show: true,
        run: () => go("/research/compare"),
      },
      {
        id: "citations",
        label: "Export citation",
        hint: "Citations",
        keywords: "citation export apa ieee bibtex cite",
        icon: Quote,
        show: true,
        run: () => go("/citations"),
      },
      {
        id: "notes",
        label: "Open notes",
        hint: "Notes",
        keywords: "notes open",
        icon: StickyNote,
        show: true,
        run: () => go("/notes"),
      },
      {
        id: "writing",
        label: "Open writing",
        hint: "Writing",
        keywords: "writing draft abstract export",
        icon: Wand2,
        show: true,
        run: () => go("/writing"),
      },
      {
        id: "new-project",
        label: "New project",
        hint: "Projects",
        keywords: "new create project",
        icon: Plus,
        show: true,
        run: () => go("/projects?new=1"),
      },
      {
        id: "ask",
        label: "Ask Soro",
        hint: "Chat",
        keywords: "ask chat soro start conversation",
        icon: MessageSquare,
        show: true,
        run: () => go(paperId ? `/papers/${paperId}/chat` : "/chat"),
      },
      {
        id: "paper-structure",
        label: "Open Structure",
        hint: "Paper",
        keywords: "structure sections headings outline",
        icon: LayoutList,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=structure`),
      },
      {
        id: "paper-evidence",
        label: "Open Evidence",
        hint: "Paper",
        keywords: "evidence grade quality bias",
        icon: FlaskConical,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=evidence`),
      },
      {
        id: "paper-graph",
        label: "Open Graph",
        hint: "Paper",
        keywords: "graph knowledge network",
        icon: Network,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=graph`),
      },
      {
        id: "paper-entities",
        label: "Open Entities",
        hint: "Paper",
        keywords: "entities pico jump entity section",
        icon: Tags,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=entities`),
      },
      {
        id: "paper-overview",
        label: "Open Overview",
        hint: "Paper",
        keywords: "overview summary paper",
        icon: FileText,
        show: paperId != null,
        run: () => go(`/papers/${paperId}`),
      },
      {
        id: "memory",
        label: "Open memory",
        hint: "Account",
        keywords: "memory preferences",
        icon: Brain,
        show: true,
        run: () => go("/memory"),
      },
      {
        id: "settings",
        label: "Settings",
        hint: "App",
        keywords: "settings preferences account",
        icon: Settings,
        show: true,
        run: () => go("/settings"),
      },
      {
        id: "home",
        label: "Go to Home",
        hint: "Navigate",
        keywords: "home dashboard continue",
        icon: Home,
        show: true,
        run: () => go("/"),
      },
      {
        id: "library",
        label: "Go to Library",
        hint: "Navigate",
        keywords: "library papers files",
        icon: Library,
        show: true,
        run: () => go("/library"),
      },
      {
        id: "projects",
        label: "Go to Projects",
        hint: "Navigate",
        keywords: "projects list",
        icon: FolderKanban,
        show: true,
        run: () => go("/projects"),
      },
    ];

    const list = commands.filter((c) => c.show);
    if (!q) {
      const order = [
        "upload",
        "search-papers",
        "compare",
        "citations",
        "ask",
        "new-project",
        "paper-evidence",
        "paper-structure",
        "paper-graph",
        "notes",
        "writing",
        "library",
        "projects",
        "home",
        "settings",
        "memory",
        "paper-entities",
        "paper-overview",
      ];
      return [...list]
        .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))
        .slice(0, 10);
    }
    return list
      .map((c) => ({
        cmd: c,
        score: scoreMatch(`${c.label} ${c.keywords} ${c.hint ?? ""}`, q),
      }))
      .filter((x) => x.score >= 0)
      .sort((a, b) => b.score - a.score)
      .map((x) => x.cmd);
    // go/navigate are stable enough for palette actions
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, paperId, query]);

  const showEmpty =
    visibleCommands.length === 0 &&
    rankedPapers.length === 0 &&
    rankedProjects.length === 0 &&
    rankedChats.length === 0;

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Command palette"
      description="Find papers, run commands, navigate Soro"
    >
      <Command shouldFilter={false} className="rounded-xl">
        <CommandInput
          value={query}
          onValueChange={setQuery}
          placeholder="Search papers, projects, commands…"
        />
        <div className="flex items-center gap-2 border-b border-border px-3 py-1.5">
          <span
            className={cn(
              "rounded-md border border-border bg-muted/50 px-1.5 py-0.5",
              "text-[10px] font-medium uppercase tracking-wide text-muted-foreground",
            )}
          >
            {scope.label}
          </span>
          <span className="text-[11px] text-muted-foreground">
            ↑↓ move · Enter open · Esc close
          </span>
        </div>
        <CommandList>
          {showEmpty && <CommandEmpty>No matches.</CommandEmpty>}

          {visibleCommands.length > 0 && (
            <CommandGroup heading="Commands">
              {visibleCommands.map((c) => {
                const Icon = c.icon;
                return (
                  <CommandItem
                    key={c.id}
                    value={c.id}
                    onSelect={() => run(c.run)}
                    className="gap-2"
                  >
                    <Icon className="size-4 shrink-0 text-muted-foreground" />
                    <span className="flex-1 truncate">{c.label}</span>
                    {c.hint && (
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {c.hint}
                      </span>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          )}

          {rankedPapers.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading={q ? "Papers" : "Recent papers"}>
                {rankedPapers.map((f) => (
                  <CommandItem
                    key={`paper-${f.id}`}
                    value={`paper-${f.id}`}
                    onSelect={() => go(`/papers/${f.id}`)}
                    className="gap-2"
                  >
                    <BookOpen className="size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate">{paperTitle(f)}</span>
                    <span className="shrink-0 text-[11px] text-muted-foreground">
                      {[f.year, f.reading_status].filter(Boolean).join(" · ")}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {rankedProjects.length > 0 && (
            <>
              <CommandSeparator />
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
                    <span className="size-4 shrink-0 text-center text-sm leading-4">
                      {p.emoji || "📁"}
                    </span>
                    <span className="min-w-0 flex-1 truncate">{p.name}</span>
                    <span className="shrink-0 text-[11px] text-muted-foreground">
                      {scope.projectId === p.id ? "Active" : "Switch"}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {rankedChats.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Chats">
                {rankedChats.map((c) => (
                  <CommandItem
                    key={`chat-${c.id}`}
                    value={`chat-${c.id}`}
                    onSelect={() => go(chatPath(c))}
                    className="gap-2"
                  >
                    <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate">
                      {c.title || "Untitled chat"}
                    </span>
                    <span className="shrink-0 text-[11px] text-muted-foreground">
                      {c.file_id ? "Paper" : c.project_id ? "Project" : "Ask"}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
