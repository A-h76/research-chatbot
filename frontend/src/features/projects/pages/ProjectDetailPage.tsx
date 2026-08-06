import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ChevronLeft,
  Pencil,
  MessageSquare,
  Brain,
  FileText,
  CheckCircle2,
  BookMarked,
  BookOpen,
  FolderKanban,
  Library,
  GitCompare,
  StickyNote,
  HelpCircle,
  Sparkles,
  PenLine,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ProjectDialog } from "../components/ProjectDialog";
import { ProjectQuestionsPanel } from "../components/ProjectQuestionsPanel";
import { ProjectPapersPanel } from "../components/ProjectPapersPanel";
import { ProjectNotesPanel } from "../components/ProjectNotesPanel";
import { ProjectInsightsPanel } from "../components/ProjectInsightsPanel";
import { ProjectResearchConsole } from "../components/ProjectResearchConsole";
import { ProjectChatPanel } from "../components/ProjectChatPanel";
import { useProjectHub } from "../useProjects";
import { useUI } from "@/context/UIContext";
import { ApiError } from "@/lib/apiClient";
import { cn, formatDate } from "@/lib/utils";
import {
  ResearchPipelineBeam,
  pipelineIndexFromProjectStats,
} from "@/features/research-flow";
import type {
  ProjectHub,
  ProjectHubInsight,
  ProjectHubPaper,
  ProjectHubQuestion,
} from "@/types/api";

export type ProjectTab =
  | "overview"
  | "papers"
  | "notes"
  | "questions"
  | "insights"
  | "compare"
  | "research"
  | "chat";

const TABS: { id: ProjectTab; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <FolderKanban className="size-3.5" /> },
  { id: "papers", label: "Papers", icon: <FileText className="size-3.5" /> },
  { id: "notes", label: "Notes", icon: <StickyNote className="size-3.5" /> },
  { id: "questions", label: "Questions", icon: <HelpCircle className="size-3.5" /> },
  { id: "insights", label: "Insights & Memory", icon: <Sparkles className="size-3.5" /> },
  { id: "research", label: "Research", icon: <GitCompare className="size-3.5" /> },
  { id: "chat", label: "Chat", icon: <MessageSquare className="size-3.5" /> },
];

function StatBadge({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <span className="text-primary">{icon}</span>
      <span className="font-medium text-foreground">{value}</span>
      <span>{label}</span>
    </div>
  );
}

function MiniProgress({
  reading,
  read,
  unread,
}: {
  reading: number;
  read: number;
  unread: number;
}) {
  const total = reading + read + unread;
  if (total === 0) return null;
  const pct = (n: number) => Math.round((n / total) * 100);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Reading progress</span>
        <span className="tabular-nums">{pct(read)}% read</span>
      </div>
      <div className="flex h-px overflow-hidden bg-border">
        <div className="bg-sem-ready" style={{ width: `${pct(read)}%` }} />
        <div className="bg-sem-warn" style={{ width: `${pct(reading)}%` }} />
      </div>
    </div>
  );
}

const RS_ICON = {
  read: <CheckCircle2 className="size-3.5 shrink-0 text-sem-ready" />,
  reading: <BookMarked className="size-3.5 shrink-0 text-sem-warn" />,
  unread: <BookOpen className="size-3.5 shrink-0 text-muted-foreground" />,
};

function PaperRow({
  paper,
  onClick,
}: {
  paper: ProjectHubPaper;
  onClick: () => void;
}) {
  const title = paper.title || paper.name;
  const rs = paper.reading_status;
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-muted/40"
    >
      <div className="flex size-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted/30">
        <FileText className="size-3.5 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium" title={title}>
          {title}
        </p>
        <p className="truncate text-[11px] text-muted-foreground">
          {[paper.authors?.split(";")[0]?.trim(), paper.year].filter(Boolean).join(" · ") ||
            "No metadata"}
        </p>
      </div>
      {RS_ICON[rs]}
    </button>
  );
}

function InsightRow({ insight }: { insight: ProjectHubInsight }) {
  return (
    <div className="flex items-center gap-2.5 rounded-md border border-border px-3 py-2">
      <Sparkles className="size-3.5 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium">{insight.title}</p>
        <p className="text-[11px] capitalize text-muted-foreground">{insight.kind}</p>
      </div>
    </div>
  );
}

function GettingStartedChecklist({
  onTab,
  onWriteDraft,
}: {
  onTab: (t: ProjectTab) => void;
  onWriteDraft: () => void;
}) {
  const steps = [
    {
      title: "Add papers to this project",
      detail: "Upload PDFs or assign papers from your library.",
      action: () => onTab("papers"),
      label: "Go to Papers",
    },
    {
      title: "Wait for analysis to finish",
      detail: "Each paper is indexed so research can cite evidence.",
      action: null,
      label: null,
    },
    {
      title: "Write an evidence-grounded draft",
      detail: "Review evidence on the Writing desk, generate a draft, revise, and save.",
      action: onWriteDraft,
      label: "Open Writing",
    },
  ];

  return (
    <section className="rounded-md border border-border bg-muted/20 p-3.5">
      <h2 className="text-sm font-semibold">Getting started</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Research workflow — complete these steps to unlock project research.
      </p>
      <ol className="mt-3 space-y-2.5">
        {steps.map((step, i) => (
          <li key={step.title} className="flex gap-2.5">
            <span className="flex size-5 shrink-0 items-center justify-center rounded border border-primary/30 bg-primary/10 text-[11px] font-semibold text-primary">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{step.title}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{step.detail}</p>
              {step.action && step.label && (
                <button
                  type="button"
                  onClick={step.action}
                  className="mt-1.5 text-xs font-medium text-primary hover:underline"
                >
                  {step.label} →
                </button>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function OverviewTab({
  hub,
  onOpenPaper,
  onTab,
  onWriteDraft,
  onReviewEvidence,
}: {
  hub: ProjectHub;
  onOpenPaper: (id: number) => void;
  onTab: (t: ProjectTab) => void;
  onWriteDraft: () => void;
  onReviewEvidence: () => void;
}) {
  const {
    project,
    stats,
    recent_papers,
    recent_notes,
    recent_insights,
    open_questions,
    pipeline_summary,
    analysis_summary,
  } = hub;
  const pipeTotal =
    pipeline_summary.done +
    pipeline_summary.running +
    pipeline_summary.pending +
    pipeline_summary.failed +
    pipeline_summary.partial;

  return (
    <div className="space-y-5" data-density="high">
      {stats.papers === 0 && (
        <GettingStartedChecklist onTab={onTab} onWriteDraft={onWriteDraft} />
      )}

      {stats.papers > 0 && (
        <section className="rounded-md border border-border bg-muted/20 p-3.5">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            What am I working on?
          </p>
          <h2 className="mt-1 text-sm font-semibold">Literature review workflow</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Project → Evidence → Draft → Revise → Save — without leaving Dhund.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" className="gap-1.5" onClick={onWriteDraft}>
              <PenLine className="size-3.5" /> Write draft
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5" onClick={onReviewEvidence}>
              <CheckCircle2 className="size-3.5" /> Review evidence
            </Button>
          </div>
        </section>
      )}

      <ResearchPipelineBeam
        activeIndex={pipelineIndexFromProjectStats({
          papers: stats.papers,
          notes_count: stats.notes,
          writing_count: stats.chats > 0 && stats.notes > 0 ? 1 : 0,
          evidence_count: pipeline_summary.done > 0 ? pipeline_summary.done : 0,
        })}
      />

      <div className="flex flex-wrap gap-4">
        <StatBadge icon={<FileText className="size-4" />} value={stats.papers} label="papers" />
        <StatBadge icon={<StickyNote className="size-4" />} value={stats.notes} label="notes" />
        <StatBadge
          icon={<HelpCircle className="size-4" />}
          value={stats.open_questions}
          label="questions"
        />
        <StatBadge icon={<Sparkles className="size-4" />} value={stats.insights} label="insights" />
        <StatBadge icon={<MessageSquare className="size-4" />} value={stats.chats} label="chats" />
      </div>

      {open_questions.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Open questions</h2>
            <button
              type="button"
              onClick={() => onTab("questions")}
              className="text-xs text-primary hover:underline"
            >
              Manage
            </button>
          </div>
          <ul className="space-y-1.5">
            {open_questions.map((q: ProjectHubQuestion) => (
              <li
                key={q.id}
                className="flex items-start gap-2 rounded-md border border-border px-3 py-2 text-sm"
              >
                <HelpCircle className="mt-0.5 size-3.5 shrink-0 text-sem-warn" />
                <span className="min-w-0 flex-1 leading-relaxed">{q.text}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {stats.papers > 0 && (
        <MiniProgress reading={stats.reading} read={stats.read} unread={stats.unread} />
      )}

      {pipeTotal > 0 && (
        <div className="dhund-enter rounded-md border border-border bg-card px-3 py-2.5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Corpus pipeline · </span>
          {analysis_summary.ready} ready for cross-paper research
          {analysis_summary.running > 0 ? ` · ${analysis_summary.running} analysing` : ""}
          {analysis_summary.pending > 0 ? ` · ${analysis_summary.pending} waiting` : ""}
          {analysis_summary.failed > 0 ? ` · ${analysis_summary.failed} need attention` : ""}
          {pipeline_summary.running + pipeline_summary.pending > 0 ? (
            <span className="mt-1 block text-[11px]">
              Upload/extract may finish before structured analysis — open a paper to watch
              stage-by-stage progress.
            </span>
          ) : null}
        </div>
      )}

      {project.instructions && (
        <section className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            AI Instructions
          </h2>
          <div className="rounded-md border border-border bg-muted/20 p-3">
            <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
              {project.instructions}
            </p>
          </div>
        </section>
      )}

      <div className="flex items-start gap-2.5 rounded-md border border-border bg-muted/15 px-3 py-2.5">
        <Brain className="mt-0.5 size-3.5 shrink-0 text-primary" />
        <div>
          <p className="text-[13px] font-medium">Isolated knowledge context</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Chat and research in this project only retrieve from papers assigned here.
          </p>
        </div>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Papers ({stats.papers})</h2>
          <button
            type="button"
            onClick={() => onTab("papers")}
            className="text-xs text-primary hover:underline"
          >
            View all
          </button>
        </div>
        {recent_papers.length === 0 ? (
          <div className="rounded-md border border-dashed border-border px-3 py-4">
            <p className="text-sm text-muted-foreground">No papers yet.</p>
            <button
              type="button"
              onClick={() => onTab("papers")}
              className="mt-2 text-xs font-medium text-primary hover:underline"
            >
              Next · Add papers →
            </button>
          </div>
        ) : (
          <div className="space-y-0.5">
            {recent_papers.map((p) => (
              <PaperRow key={p.id} paper={p} onClick={() => onOpenPaper(p.id)} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Notes ({stats.notes})</h2>
          <button
            type="button"
            onClick={() => onTab("notes")}
            className="text-xs text-primary hover:underline"
          >
            View all
          </button>
        </div>
        {recent_notes.length === 0 ? (
          <div className="rounded-md border border-dashed border-border px-3 py-4">
            <p className="text-sm text-muted-foreground">No notes yet.</p>
            <button
              type="button"
              onClick={() => onTab("notes")}
              className="mt-2 text-xs font-medium text-primary hover:underline"
            >
              Next · Capture a note →
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {recent_notes.map((n) => (
              <div key={n.id} className="rounded-md border border-border px-3 py-2">
                <p className="text-sm font-medium truncate">{n.title || "Untitled note"}</p>
                <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                  {n.content_preview || "Empty"}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Insights ({stats.insights})</h2>
          <button
            type="button"
            onClick={() => onTab("insights")}
            className="text-xs text-primary hover:underline"
          >
            View all
          </button>
        </div>
        {recent_insights.length === 0 ? (
          <div className="rounded-md border border-dashed border-border px-3 py-4">
            <p className="text-sm text-muted-foreground">
              Insights appear after you run project research over your papers.
            </p>
            <button
              type="button"
              onClick={() => onTab("research")}
              className="mt-2 text-xs font-medium text-primary hover:underline"
            >
              Next · Open Research →
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {recent_insights.map((i) => (
              <InsightRow key={i.id} insight={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const parsed = projectId != null ? Number(projectId) : NaN;
  const id = Number.isFinite(parsed) ? parsed : null;

  const { data: hub, isLoading, isError, error, refetch, isFetching } = useProjectHub(id);
  const { setCurrentProjectId } = useUI();
  const [editOpen, setEditOpen] = useState(false);

  useEffect(() => {
    if (id != null) setCurrentProjectId(id);
  }, [id, setCurrentProjectId]);

  const tabParam = searchParams.get("tab") as ProjectTab | null;
  const activeTab: ProjectTab = useMemo(() => {
    if (tabParam === "compare") return "research";
    if (tabParam && TABS.some((t) => t.id === tabParam)) return tabParam;
    return "overview";
  }, [tabParam]);

  function setTab(t: ProjectTab) {
    if (t === "overview") {
      setSearchParams({}, { replace: true });
    } else {
      setSearchParams({ tab: t }, { replace: true });
    }
  }

  function openPaper(fileId: number) {
    if (id != null) setCurrentProjectId(id);
    navigate(`/papers/${fileId}`);
  }

  function openLibrary() {
    if (!id) return;
    setCurrentProjectId(id);
    navigate("/library");
  }

  function openAsk() {
    if (!id) return;
    setCurrentProjectId(id);
    setTab("chat");
  }

  function openCompare() {
    if (!id) return;
    setCurrentProjectId(id);
    setTab("research");
  }

  function openWriting(opts?: { focus?: "evidence"; action?: "lit-review" }) {
    if (!id) return;
    setCurrentProjectId(id);
    const params = new URLSearchParams();
    if (opts?.focus) params.set("focus", opts.focus);
    if (opts?.action) params.set("action", opts.action);
    const qs = params.toString();
    navigate(qs ? `/writing?${qs}` : "/writing");
  }

  function openWriteDraft() {
    openWriting({ action: "lit-review" });
  }

  function openReviewEvidence() {
    openWriting({ focus: "evidence" });
  }

  if (isLoading) {
    return (
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-10 w-full" />
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-md" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const isNotFound =
    id == null ||
    (isError && error instanceof ApiError && error.status === 404) ||
    (!isError && !hub);

  if (isNotFound) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3 px-6">
          <FolderKanban className="mx-auto size-10 text-muted-foreground" />
          <p className="text-sm font-medium">Project not found</p>
          <p className="text-xs text-muted-foreground">
            This project doesn’t exist or you don’t have access to it.
          </p>
          <Button variant="outline" size="sm" onClick={() => navigate("/projects")}>
            Back to projects
          </Button>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3 px-6">
          <FolderKanban className="mx-auto size-10 text-muted-foreground" />
          <p className="text-sm font-medium">Couldn’t load this project</p>
          <p className="text-xs text-muted-foreground">
            Check your connection and try again.
          </p>
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={isFetching}
              onClick={() => void refetch()}
            >
              Retry
            </Button>
            <Button variant="ghost" size="sm" onClick={() => navigate("/projects")}>
              Back to projects
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const { project, stats, recent_papers } = hub;

  return (
    <div className="scrollbar-thin h-full overflow-y-auto" data-density="high">
      <div className="mx-auto max-w-3xl space-y-5 px-6 py-6">
        <button
          type="button"
          onClick={() => navigate("/projects")}
          className="flex items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="size-4" /> Research
        </button>

        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            What am I working on?
          </p>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted/30 text-2xl">
              {project.emoji}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold tracking-tight">{project.name}</h1>
              {project.description && (
                <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>
              )}
              {project.created_at && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Created {formatDate(project.created_at)}
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditOpen(true)}
              className="shrink-0 gap-1.5"
            >
              <Pencil className="size-3.5" /> Edit
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() =>
                recent_papers[0] ? openPaper(recent_papers[0].id) : setTab("papers")
              }
              className="gap-2"
            >
              <FileText className="size-4" />
              {stats.papers > 0 ? "Open research" : "Add papers"}
            </Button>
            <Button variant="outline" onClick={openLibrary} className="gap-2">
              <Library className="size-4" /> Library
            </Button>
            <Button variant="outline" onClick={openAsk} className="gap-2">
              <MessageSquare className="size-4" /> Ask in project
            </Button>
            <Button variant="outline" onClick={openCompare} className="gap-2">
              <GitCompare className="size-4" /> Research
            </Button>
            <Button variant="outline" onClick={openWriteDraft} className="gap-2">
              <PenLine className="size-4" /> Write draft
            </Button>
          </div>
        </motion.div>

        {/* Workspace tabs — deeper data lazy-loaded when opened */}
        <div className="sticky top-0 z-10 -mx-1 border-b border-border bg-background/95 px-1 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <nav className="flex gap-0.5 overflow-x-auto scrollbar-thin py-1" aria-label="Project sections">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] transition-colors",
                  activeTab === t.id
                    ? "bg-accent-soft font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                )}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </nav>
        </div>

        <Separator className="!mt-0" />

        {activeTab === "overview" && (
          <OverviewTab
            hub={hub}
            onOpenPaper={openPaper}
            onTab={setTab}
            onWriteDraft={openWriteDraft}
            onReviewEvidence={openReviewEvidence}
          />
        )}

        {activeTab === "papers" && id != null && (
          <ProjectPapersPanel projectId={id} />
        )}

        {activeTab === "notes" && id != null && (
          <ProjectNotesPanel projectId={id} />
        )}

        {activeTab === "questions" && id != null && (
          <ProjectQuestionsPanel projectId={id} />
        )}

        {activeTab === "insights" && id != null && (
          <ProjectInsightsPanel projectId={id} />
        )}

        {activeTab === "research" && id != null && (
          <ProjectResearchConsole projectId={id} />
        )}

        {activeTab === "chat" && id != null && (
          <ProjectChatPanel projectId={id} />
        )}
      </div>

      <ProjectDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        project={{
          id: project.id,
          name: project.name,
          emoji: project.emoji,
          description: project.description,
          instructions: project.instructions,
        }}
      />
    </div>
  );
}
