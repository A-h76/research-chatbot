import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ChevronLeft, Pencil, MessageSquare, Library, Brain,
  FileText, CheckCircle2, BookMarked, BookOpen,
  Plus, ArrowRight, Loader2, FolderKanban,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ProjectDialog } from "../components/ProjectDialog";
import { useProject } from "../useProjects";
import { useFiles } from "@/features/files/useFiles";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { cn, formatDate } from "@/lib/utils";
import type { ConversationSummary, UserFile } from "@/types/api";

// ── Small stat block ──────────────────────────────────────────────────────
function StatBadge({ icon, value, label }: {
  icon: React.ReactNode; value: number; label: string
}) {
  return (
    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <span className="text-primary">{icon}</span>
      <span className="font-medium text-foreground">{value}</span>
      <span>{label}</span>
    </div>
  );
}

// ── Reading mini progress ─────────────────────────────────────────────────
function MiniProgress({ reading, read, unread }: {
  reading: number; read: number; unread: number;
}) {
  const total = reading + read + unread;
  if (total === 0) return null;
  const pct = (n: number) => Math.round((n / total) * 100);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Reading progress</span>
        <span>{pct(read)}% read</span>
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="bg-emerald-500" style={{ width: `${pct(read)}%` }} />
        <div className="bg-amber-400"   style={{ width: `${pct(reading)}%` }} />
      </div>
      <div className="flex gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-emerald-500" /> {read} read
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-amber-400" /> {reading} reading
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-muted-foreground/30" /> {unread} unread
        </span>
      </div>
    </div>
  );
}

// ── Paper row ──────────────────────────────────────────────────────────────
const RS_ICON = {
  read:    <CheckCircle2 className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />,
  reading: <BookMarked   className="size-3.5 shrink-0 text-amber-600  dark:text-amber-400" />,
  unread:  <BookOpen     className="size-3.5 shrink-0 text-muted-foreground" />,
};

function PaperRow({ file, onClick }: { file: UserFile; onClick: () => void }) {
  const title = file.title || file.name;
  const rs = (file.reading_status ?? "unread") as "read" | "reading" | "unread";
  const processing = file.meta_status === "pending" || file.meta_status === "running";

  return (
    <button
      onClick={onClick}
      className="group flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition-colors hover:bg-muted/50"
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft">
        <FileText className="size-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium" title={title}>{title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {[file.authors?.split(";")[0]?.trim(), file.year].filter(Boolean).join(" · ") || "No metadata"}
        </p>
      </div>
      <div className="flex items-center gap-1.5">
        {processing && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
        {RS_ICON[rs]}
      </div>
    </button>
  );
}

// ── Chat row ───────────────────────────────────────────────────────────────
function ChatRow({ convo, onClick }: { convo: ConversationSummary; onClick: () => void }) {
  const isPaper = convo.file_id !== null;
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition-colors hover:bg-muted/50"
    >
      <div className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg",
        isPaper ? "bg-accent-soft" : "bg-muted",
      )}>
        <MessageSquare className={cn("size-4", isPaper ? "text-primary" : "text-muted-foreground")} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{convo.title}</p>
        {isPaper && <p className="text-[10px] text-primary/80">Paper chat</p>}
      </div>
      <ArrowRight className="size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
    </button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────
export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate      = useNavigate();
  const id            = projectId ? Number(projectId) : null;

  const { data: project, isLoading } = useProject(id);
  const { setCurrentProjectId }      = useUI();

  // Scoped lists
  const { data: filesData } = useFiles({ project_id: id, kind: "document", limit: 8 });
  const { data: allConvos = [] } = useConversations();
  const scopedConvos = allConvos.filter((c) => c.project_id === id).slice(0, 6);

  const [editOpen, setEditOpen] = useState(false);

  function openProject() {
    if (!id) return;
    setCurrentProjectId(id);
    navigate("/chat");
  }

  function openLibrary() {
    if (!id) return;
    setCurrentProjectId(id);
    navigate("/files");
  }

  if (isLoading) {
    return (
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
          </div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3">
          <FolderKanban className="mx-auto size-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Project not found.</p>
          <Button variant="outline" size="sm" onClick={() => navigate("/projects")}>
            Back to projects
          </Button>
        </div>
      </div>
    );
  }

  const stats = project.stats;
  const papers = filesData?.items ?? [];

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8 space-y-8">

        {/* Back nav */}
        <button
          onClick={() => navigate("/projects")}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft className="size-4" /> Research Projects
        </button>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="flex items-start gap-4">
            <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-accent-soft text-3xl">
              {project.emoji}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold tracking-tight">{project.name}</h1>
              {project.description && (
                <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>
              )}
              {project.created_at && (
                <p className="mt-1 text-xs text-muted-foreground/70">
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

          {/* Stat row */}
          <div className="flex flex-wrap gap-4">
            <StatBadge icon={<FileText className="size-4" />} value={stats.papers} label="papers" />
            <StatBadge icon={<MessageSquare className="size-4" />} value={stats.chats} label="chats" />
            {stats.memories > 0 && (
              <StatBadge icon={<Brain className="size-4" />} value={stats.memories} label="memories" />
            )}
          </div>

          {/* Reading progress */}
          {stats.papers > 0 && (
            <MiniProgress
              reading={stats.reading}
              read={stats.read}
              unread={stats.unread}
            />
          )}

          {/* Quick actions */}
          <div className="flex flex-wrap gap-2">
            <Button onClick={openProject} className="gap-2">
              <MessageSquare className="size-4" /> Chat in this project
            </Button>
            <Button variant="outline" onClick={openLibrary} className="gap-2">
              <Library className="size-4" /> View library
            </Button>
          </div>
        </motion.div>

        <Separator />

        {/* Instructions */}
        {project.instructions && (
          <section className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              AI Instructions
            </h2>
            <div className="rounded-xl border border-border bg-muted/30 p-3.5">
              <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                {project.instructions}
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              These instructions are injected into every AI chat in this project.
            </p>
          </section>
        )}

        {/* RAG isolation note */}
        <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-accent-soft/50 p-4">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Brain className="size-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium">Isolated knowledge context</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              When you chat inside this project, the AI only retrieves from papers assigned here —
              not from your full library. Upload papers to this project to keep research focused.
            </p>
          </div>
        </div>

        {/* Papers */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Papers ({stats.papers})</h2>
            <button
              onClick={openLibrary}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
            >
              View all <ArrowRight className="size-3" />
            </button>
          </div>

          {papers.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border p-6 text-center space-y-2">
              <FileText className="mx-auto size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No papers in this project yet.</p>
              <p className="text-xs text-muted-foreground">
                Attach a PDF in chat — it'll be assigned here automatically.
              </p>
            </div>
          ) : (
            <div className="rounded-2xl border border-border bg-card divide-y divide-border overflow-hidden">
              {papers.map((f) => (
                <PaperRow
                  key={f.id}
                  file={f}
                  onClick={() => navigate(`/papers/${f.id}`)}
                />
              ))}
              {(filesData?.total ?? 0) > papers.length && (
                <button
                  onClick={openLibrary}
                  className="flex w-full items-center justify-center gap-1.5 py-2.5 text-xs text-muted-foreground hover:text-primary transition-colors"
                >
                  {(filesData?.total ?? 0) - papers.length} more papers
                  <ArrowRight className="size-3" />
                </button>
              )}
            </div>
          )}
        </section>

        {/* Recent chats */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent Chats ({stats.chats})</h2>
            <button
              onClick={openProject}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
            >
              New chat <Plus className="size-3" />
            </button>
          </div>

          {scopedConvos.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border p-6 text-center">
              <p className="text-sm text-muted-foreground">No chats yet.</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={openProject}
              >
                Start a chat in this project
              </Button>
            </div>
          ) : (
            <div className="rounded-2xl border border-border bg-card divide-y divide-border overflow-hidden">
              {scopedConvos.map((c) => (
                <ChatRow
                  key={c.id}
                  convo={c}
                  onClick={() =>
                    c.file_id
                      ? navigate(`/papers/${c.file_id}/chat/${c.id}`)
                      : navigate(`/c/${c.id}`)
                  }
                />
              ))}
            </div>
          )}
        </section>

        <div className="h-6" />
      </div>

      {/* Edit dialog */}
      <ProjectDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        project={project}
      />
    </div>
  );
}
