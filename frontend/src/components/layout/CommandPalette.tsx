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
  FileDown,
  FileText,
  FolderKanban,
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
  Layers,
} from "lucide-react";
import { useAllFiles } from "@/features/files/useFiles";
import { useProjects } from "@/features/projects/useProjects";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI } from "@/context/UIContext";
import type { ConversationSummary, Project, UserFile } from "@/types/api";

type ScopeKind = "paper" | "project" | "library" | "global";

type Scope = {
  kind: ScopeKind;
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

function parsePrefix(raw: string): { mode: PrefixMode; q: string } {
  const t = raw.trimStart();
  if (t.startsWith(">")) return { mode: "command", q: t.slice(1).trim().toLowerCase() };
  if (t.startsWith("@")) return { mode: "mention", q: t.slice(1).trim().toLowerCase() };
  if (t.startsWith("#")) return { mode: "entity", q: t.slice(1).trim().toLowerCase() };
  if (t.startsWith("/")) return { mode: "skill", q: t.slice(1).trim().toLowerCase() };
  return { mode: "none", q: t.trim().toLowerCase() };
}

function filterCmds(list: Cmd[], q: string): Cmd[] {
  if (!q) return list.filter((c) => c.show);
  return list
    .filter((c) => c.show)
    .map((c) => ({
      cmd: c,
      score: scoreMatch(`${c.label} ${c.keywords} ${c.hint ?? ""}`, q),
    }))
    .filter((x) => x.score >= 0)
    .sort((a, b) => b.score - a.score)
    .map((x) => x.cmd);
}

/**
 * Research Command Center — ⌘K / sidebar Search.
 * Places stay in the sidebar; this is actions + find across the Research OS.
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

  const { mode, q } = parsePrefix(query);
  const paperId = scope.paperId;

  function go(path: string) {
    setOpen(false);
    navigate(path);
  }

  function run(fn: () => void) {
    setOpen(false);
    fn();
  }

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

  const quickActions: Cmd[] = useMemo(
    () => [
      {
        id: "ask",
        label: "Ask Dhund",
        hint: "Chat",
        keywords: "ask chat agent conversation",
        icon: MessageSquare,
        show: true,
        run: () => go(paperId ? `/papers/${paperId}/chat` : "/chat"),
      },
      {
        id: "new-project",
        label: "Create project",
        hint: "Create",
        keywords: "new create project research",
        icon: Plus,
        show: true,
        run: () => go("/projects?new=1"),
      },
      {
        id: "create-writing",
        label: "Create writing",
        hint: "Create",
        keywords: "write literature review manuscript draft",
        icon: PenLine,
        show: true,
        run: () => go("/writing?action=lit-review"),
      },
      {
        id: "upload",
        label: "Upload paper",
        hint: "Library",
        keywords: "upload pdf paper document",
        icon: Upload,
        show: true,
        run: () => go("/library?upload=1"),
      },
      {
        id: "import-doi",
        label: "Import DOI",
        hint: "Library",
        keywords: "import doi crossref discover",
        icon: Link2,
        show: true,
        run: () => go("/library?provider=bibtex#import"),
      },
      {
        id: "import-pmid",
        label: "Import PMID",
        hint: "Library",
        keywords: "import pmid pubmed",
        icon: Link2,
        show: true,
        run: () => go("/library?provider=bibtex#import"),
      },
      {
        id: "new-collection",
        label: "New collection",
        hint: "Library",
        keywords: "collection folder organize",
        icon: Layers,
        show: true,
        run: () => go("/library?collections=1"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [paperId],
  );

  const jumpTo: Cmd[] = useMemo(
    () => [
      {
        id: "home",
        label: "Home",
        hint: "Jump",
        keywords: "home launchpad dashboard continue",
        icon: Home,
        show: true,
        run: () => go("/home"),
      },
      {
        id: "library",
        label: "Library",
        hint: "Jump",
        keywords: "library papers files",
        icon: Library,
        show: true,
        run: () => go("/library"),
      },
      {
        id: "projects",
        label: "Projects",
        hint: "Jump",
        keywords: "projects research list all",
        icon: FolderKanban,
        show: true,
        run: () => go("/projects"),
      },
      {
        id: "writing-desk",
        label: "Writing",
        hint: "Jump",
        keywords: "writing desk draft manuscript",
        icon: Wand2,
        show: true,
        run: () => go("/writing"),
      },
      {
        id: "notes",
        label: "Notes",
        hint: "Jump",
        keywords: "notes",
        icon: StickyNote,
        show: true,
        run: () => go("/notes"),
      },
      {
        id: "citations",
        label: "Citations",
        hint: "Jump",
        keywords: "citations export apa bibtex",
        icon: Quote,
        show: true,
        run: () => go("/citations"),
      },
      {
        id: "settings",
        label: "Settings",
        hint: "Jump",
        keywords: "settings account preferences integrations",
        icon: Settings,
        show: true,
        run: () => go("/settings"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const knowledge: Cmd[] = useMemo(
    () => [
      {
        id: "paper-overview",
        label: "Research profile",
        hint: "Knowledge",
        keywords: "research profile overview summary",
        icon: FileText,
        show: paperId != null,
        run: () => go(`/papers/${paperId}`),
      },
      {
        id: "writing-evidence",
        label: "Evidence",
        hint: "Knowledge",
        keywords: "evidence inspector verify passages",
        icon: FlaskConical,
        show: true,
        run: () =>
          go(paperId ? `/papers/${paperId}?tab=evidence` : "/writing?focus=evidence"),
      },
      {
        id: "paper-graph",
        label: "Knowledge graph",
        hint: "Knowledge",
        keywords: "graph knowledge network",
        icon: Network,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=graph`),
      },
      {
        id: "paper-entities",
        label: "Entities",
        hint: "Knowledge",
        keywords: "entities concepts pico",
        icon: Tags,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=entities`),
      },
      {
        id: "paper-structure",
        label: "Structure",
        hint: "Knowledge",
        keywords: "structure sections outline narrative",
        icon: LayoutList,
        show: paperId != null,
        run: () => go(`/papers/${paperId}?tab=structure`),
      },
      {
        id: "theme-discovery",
        label: "Themes",
        hint: "Knowledge",
        keywords: "themes clusters discovery narrative",
        icon: Tags,
        show: true,
        run: () => go("/research/compare?tab=themes"),
      },
      {
        id: "memory",
        label: "Memory",
        hint: "Knowledge",
        keywords: "memory preferences claims",
        icon: Brain,
        show: true,
        run: () => go("/memory"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [paperId],
  );

  const skills: Cmd[] = useMemo(
    () => [
      {
        id: "skill-compare",
        label: "Compare",
        hint: "Skill",
        keywords: "compare papers gaps",
        icon: GitCompare,
        show: true,
        run: () => go("/research/compare?tab=matrix"),
      },
      {
        id: "skill-summarize",
        label: "Summarize",
        hint: "Skill",
        keywords: "summarize overview profile",
        icon: BookOpen,
        show: true,
        run: () => go(paperId ? `/papers/${paperId}` : "/library"),
      },
      {
        id: "skill-extract",
        label: "Extract",
        hint: "Skill",
        keywords: "extract pico structured",
        icon: ClipboardList,
        show: true,
        run: () => go("/research/compare?tab=extract"),
      },
      {
        id: "skill-review",
        label: "Reviewer",
        hint: "Skill",
        keywords: "review verify evidence writing",
        icon: FlaskConical,
        show: true,
        run: () => go("/writing?focus=evidence"),
      },
      {
        id: "skill-write",
        label: "Write",
        hint: "Skill",
        keywords: "write literature review",
        icon: PenLine,
        show: true,
        run: () => go("/writing?action=lit-review"),
      },
      {
        id: "skill-matrix",
        label: "Evidence matrix",
        hint: "Skill",
        keywords: "matrix methods findings",
        icon: Table2,
        show: true,
        run: () => go("/research/compare?tab=matrix"),
      },
      {
        id: "skill-export",
        label: "Export",
        hint: "Skill",
        keywords: "export markdown download",
        icon: FileDown,
        show: true,
        run: () => go("/writing?tab=export"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [paperId],
  );

  const directCommands: Cmd[] = useMemo(
    () => [
      ...quickActions,
      ...skills,
      {
        id: "search-papers",
        label: "Search papers page",
        hint: "Command",
        keywords: "search find library rag",
        icon: Search,
        show: true,
        run: () => go("/search"),
      },
      {
        id: "zotero",
        label: "Connect Zotero",
        hint: "Command",
        keywords: "zotero import",
        icon: Link2,
        show: true,
        run: () => go("/library?provider=zotero#import"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [quickActions, skills],
  );

  const idle = mode === "none" && !q;
  const searching = mode === "none" && Boolean(q);

  const shownQuick = filterCmds(quickActions, idle ? "" : q).slice(0, idle ? 7 : 8);
  const shownJump = filterCmds(jumpTo, idle ? "" : q);
  const shownKnowledge = filterCmds(knowledge, idle ? "" : q);
  const shownSkills = filterCmds(skills, q);
  const shownCommands = filterCmds(directCommands, q);

  const showEmpty =
    !idle &&
    shownQuick.length === 0 &&
    shownJump.length === 0 &&
    shownKnowledge.length === 0 &&
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

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Search Dhund"
      description="Research command center — find papers, projects, evidence, and run actions"
    >
      <Command shouldFilter={false} className="rounded-xl">
        <CommandInput
          value={query}
          onValueChange={setQuery}
          placeholder="Search papers, projects, evidence, entities, citations…"
        />
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-3 py-1.5 text-[11px] text-muted-foreground">
          <span className="rounded-md border border-border bg-muted/40 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide">
            {scope.label}
          </span>
          <span>
            <kbd className="opacity-70">/</kbd> skills ·{" "}
            <kbd className="opacity-70">@</kbd> mention ·{" "}
            <kbd className="opacity-70">#</kbd> entities ·{" "}
            <kbd className="opacity-70">&gt;</kbd> commands
          </span>
        </div>
        <CommandList className="max-h-[min(420px,55vh)]">
          {showEmpty && <CommandEmpty>No matches.</CommandEmpty>}

          {mode === "skill" && (
            <CommandGroup heading="Skills">{shownSkills.map(renderCmd)}</CommandGroup>
          )}

          {mode === "command" && (
            <CommandGroup heading="Commands">{shownCommands.map(renderCmd)}</CommandGroup>
          )}

          {mode === "entity" && (
            <CommandGroup heading="Entities & knowledge">
              {shownKnowledge.length > 0 ? (
                shownKnowledge.map(renderCmd)
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
              {paperId != null &&
                rankedPapers
                  .filter((f) => f.id === paperId)
                  .map((f) => (
                    <CommandItem
                      key={`ent-paper-${f.id}`}
                      value={`ent-paper-${f.id}`}
                      onSelect={() => go(`/papers/${f.id}?tab=entities`)}
                      className="gap-2"
                    >
                      <Tags className="size-4 text-muted-foreground" />
                      <span className="truncate">{paperTitle(f)} · Entities</span>
                    </CommandItem>
                  ))}
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
              {(rankedPapers.length > 0 || rankedProjects.length > 0 || rankedChats.length > 0) && (
                <CommandGroup heading="Recent">
                  {rankedProjects.slice(0, 3).map((p) => (
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
                  {rankedPapers.slice(0, 4).map((f) => (
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
              )}

              <CommandSeparator />
              <CommandGroup heading="Quick actions">{shownQuick.map(renderCmd)}</CommandGroup>
              <CommandSeparator />
              <CommandGroup heading="Jump to">{shownJump.map(renderCmd)}</CommandGroup>
              {shownKnowledge.length > 0 && (
                <>
                  <CommandSeparator />
                  <CommandGroup heading="Knowledge">{shownKnowledge.map(renderCmd)}</CommandGroup>
                </>
              )}
            </>
          )}

          {searching && (
            <>
              {shownQuick.length > 0 && (
                <CommandGroup heading="Actions">{shownQuick.map(renderCmd)}</CommandGroup>
              )}
              {rankedPapers.length > 0 && mode === "none" && (
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
              {rankedProjects.length > 0 && mode === "none" && (
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
                <CommandGroup heading="Chats">
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
              {shownJump.length > 0 && (
                <CommandGroup heading="Jump to">{shownJump.map(renderCmd)}</CommandGroup>
              )}
              {shownKnowledge.length > 0 && (
                <CommandGroup heading="Knowledge">{shownKnowledge.map(renderCmd)}</CommandGroup>
              )}
              {q && (
                <CommandGroup heading="Library">
                  <CommandItem
                    value="find-library"
                    onSelect={() => go(`/library?q=${encodeURIComponent(query.trim())}`)}
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
