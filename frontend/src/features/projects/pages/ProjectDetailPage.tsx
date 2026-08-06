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
  GitCompare,
  StickyNote,
  HelpCircle,
  Sparkles,
  PenLine,
  MoreHorizontal,
  Download,
  FlaskConical,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ProjectDialog } from "../components/ProjectDialog";
import { ProjectQuestionsPanel } from "../components/ProjectQuestionsPanel";
import { ProjectPapersPanel } from "../components/ProjectPapersPanel";
import { ProjectNotesPanel } from "../components/ProjectNotesPanel";
import { ProjectInsightsPanel } from "../components/ProjectInsightsPanel";
import { ProjectResearchConsole } from "../components/ProjectResearchConsole";
import { ProjectChatPanel } from "../components/ProjectChatPanel";
import { useProjectHub } from "../useProjects";
import {
  deriveProjectWorkspaceStage,
  projectEvidenceUrl,
  projectExportUrl,
  projectReviewUrl,
  projectWritingUrl,
  projectWorkspaceStageLabel,
} from "../projectWorkspaceNav";
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

/** In-page journey panels (primary strip). */
const JOURNEY_TABS: { id: ProjectTab; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <FolderKanban className="size-3.5" /> },
  { id: "papers", label: "Papers", icon: <FileText className="size-3.5" /> },
  { id: "research", label: "Research", icon: <GitCompare className="size-3.5" /> },
];

type JourneyLinkId = "evidence" | "writing" | "review" | "export";

const JOURNEY_LINKS: { id: JourneyLinkId; label: string; icon: React.ReactNode }[] = [
  { id: "evidence", label: "Evidence", icon: <Brain className="size-3.5" /> },
  { id: "writing", label: "Writing", icon: <PenLine className="size-3.5" /> },
  { id: "review", label: "Review", icon: <FlaskConical className="size-3.5" /> },
  { id: "export", label: "Export", icon: <Download className="size-3.5" /> },
];

/** Secondary surfaces — overflow “More”. */
const MORE_TABS: { id: ProjectTab; label: string; icon: React.ReactNode }[] = [
  { id: "notes", label: "Notes", icon: <StickyNote className="size-3.5" /> },
  { id: "questions", label: "Questions", icon: <HelpCircle className="size-3.5" /> },
  { id: "insights", label: "Insights", icon: <Sparkles className="size-3.5" /> },
  { id: "chat", label: "Ask", icon: <MessageSquare className="size-3.5" /> },
];

const HUB_TAB_IDS: ProjectTab[] = [
  "overview",
  "papers",
  "notes",
  "questions",
  "insights",
  "research",
  "chat",
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
      label: "Next · Papers",
    },
    {
      title: "Wait for analysis to finish",
      detail: "Each paper is indexed so research can cite evidence.",
      action: null,
      label: null,
    },
    {
      title: "Write an evidence-grounded draft",
      detail: "Open Evidence, draft on Writing, then Review and Export.",
      action: onWriteDraft,
      label: "Next · Writing",
    },
  ];

  return (
    <section className="rounded-md border border-border bg-muted/20 p-3.5">
      <h2 className="text-sm font-semibold">Getting started</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Journey: Papers → Research → Evidence → Writing → Review → Export.
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
  onOpenResearch,
  nextLabel,
  onNext,
}: {
  hub: ProjectHub;
  onOpenPaper: (id: number) => void;
  onTab: (t: ProjectTab) => void;
  onWriteDraft: () => void;
  onReviewEvidence: () => void;
  onOpenResearch: () => void;
  nextLabel: string;
  onNext: () => void;
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
            Next step
          </p>
          <h2 className="mt-1 text-sm font-semibold">{nextLabel}</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {analysis_summary.ready}/{stats.papers} papers analysed
            {pipeline_summary.running + pipeline_summary.pending > 0
              ? ` · ${pipeline_summary.running + pipeline_summary.pending} still processing`
              : ""}
            . Continue Evidence → Writing → Review → Export when ready.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" className="gap-1.5" onClick={onNext}>
              <ArrowRight className="size-3.5" /> {nextLabel}
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5" onClick={onReviewEvidence}>
              <Brain className="size-3.5" /> Evidence
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5" onClick={onWriteDraft}>
              <PenLine className="size-3.5" /> Writing
            </Button>
            <Button size="sm" variant="ghost" className="gap-1.5" onClick={onOpenResearch}>
              <GitCompare className="size-3.5" /> Research
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
        <StatBadge
          icon={<CheckCircle2 className="size-4" />}
          value={analysis_summary.ready}
          label="ready"
        />
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

function ProjectContextBar({
  hub,
  nextLabel,
  onNext,
}: {
  hub: ProjectHub;
  nextLabel: string;
  onNext: () => void;
}) {
  const { project, stats, analysis_summary } = hub;
  const stage = deriveProjectWorkspaceStage({
    papers: stats.papers,
    analysisReady: analysis_summary.ready,
    notes: stats.notes,
    openQuestions: stats.open_questions,
    insights: stats.insights,
    chats: stats.chats,
  });
  const goal =
    (project.description?.trim() ||
      (project.instructions?.trim()
        ? project.instructions.trim().slice(0, 140) +
          (project.instructions.trim().length > 140 ? "…" : "")
        : "")) ||
    "No project goal set yet — edit to add one.";

  return (
    <div
      className="flex flex-col gap-2.5 rounded-md border border-border bg-muted/20 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3"
      data-testid="project-context-bar"
    >
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-medium text-foreground">
            {projectWorkspaceStageLabel(stage)}
          </span>
          <span className="text-[11px] tabular-nums text-muted-foreground">
            {analysis_summary.ready}/{stats.papers} ready
          </span>
          <span className="text-[11px] tabular-nums text-muted-foreground">
            · {stats.notes} notes
          </span>
          <span className="text-[11px] tabular-nums text-muted-foreground">
            · {stats.open_questions} questions
          </span>
        </div>
        <p className="truncate text-[12px] text-muted-foreground" title={goal}>
          {goal}
        </p>
      </div>
      <Button size="sm" className="shrink-0 gap-1.5" onClick={onNext}>
        <ArrowRight className="size-3.5" />
        Next · {nextLabel}
      </Button>
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
    if (tabParam && HUB_TAB_IDS.includes(tabParam)) return tabParam;
    return "overview";
  }, [tabParam]);

  const moreActive = MORE_TABS.some((t) => t.id === activeTab);

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

  function openJourneyLink(link: JourneyLinkId) {
    if (!id) return;
    setCurrentProjectId(id);
    switch (link) {
      case "evidence":
        navigate(projectEvidenceUrl(id));
        break;
      case "writing":
        navigate(projectWritingUrl(id));
        break;
      case "review":
        navigate(projectReviewUrl(id));
        break;
      case "export":
        navigate(projectExportUrl(id));
        break;
    }
  }

  function openWriteDraft() {
    if (!id) return;
    setCurrentProjectId(id);
    navigate(projectWritingUrl(id, { action: "lit-review" }));
  }

  function openReviewEvidence() {
    if (!id) return;
    setCurrentProjectId(id);
    navigate(projectEvidenceUrl(id));
  }

  const nextAction = useMemo(() => {
    if (!hub) {
      return { label: "Add papers", run: () => setTab("papers") };
    }
    const { stats, analysis_summary, recent_papers } = hub;
    const stage = deriveProjectWorkspaceStage({
      papers: stats.papers,
      analysisReady: analysis_summary.ready,
      notes: stats.notes,
      openQuestions: stats.open_questions,
      insights: stats.insights,
      chats: stats.chats,
    });
    if (stage === "papers") {
      return { label: "Add papers", run: () => setTab("papers") };
    }
    if (stage === "analysing") {
      return {
        label: "Open research",
        run: () =>
          recent_papers[0] ? openPaper(recent_papers[0].id) : setTab("papers"),
      };
    }
    if (stage === "research") {
      return { label: "Open Research", run: () => setTab("research") };
    }
    return { label: "Write draft", run: openWriteDraft };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hub, id]);

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

  const { project } = hub;

  const navBtnClass = (active: boolean) =>
    cn(
      "flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] transition-colors",
      active
        ? "bg-accent-soft font-medium text-foreground"
        : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
    );

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
            Research workspace
          </p>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted/30 text-2xl">
              {project.emoji}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold tracking-tight">{project.name}</h1>
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

          <ProjectContextBar
            hub={hub}
            nextLabel={nextAction.label}
            onNext={nextAction.run}
          />
        </motion.div>

        <div className="sticky top-0 z-10 -mx-1 border-b border-border bg-background/95 px-1 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <nav className="flex gap-0.5 overflow-x-auto scrollbar-thin py-1" aria-label="Research journey">
            {JOURNEY_TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={navBtnClass(activeTab === t.id)}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
            {JOURNEY_LINKS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => openJourneyLink(t.id)}
                className={navBtnClass(false)}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
            <DropdownMenu>
              <DropdownMenuTrigger
                className={cn(navBtnClass(moreActive), "outline-none")}
                aria-label="More project sections"
              >
                <MoreHorizontal className="size-3.5" />
                More
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-[10rem]">
                {MORE_TABS.map((t) => (
                  <DropdownMenuItem
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className="gap-2"
                  >
                    {t.icon}
                    {t.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
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
            onOpenResearch={() => setTab("research")}
            nextLabel={nextAction.label}
            onNext={nextAction.run}
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
